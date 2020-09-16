#!/usr/bin/env python3
import os

from Aws.Clients import Ecs, Ssm
from Aws.Clients import CloudWatch
from datetime import datetime
from Deployment.AwsCli import AwsCli
from Deployment.ConfigurationFile import ConfigurationFile
from Deployment.Docker import Docker
from Deployment.DockerCompose import DockerCompose
from Deployment.GitHub import GitHub


def to_camel_case(value: str) -> str:
    """
    Convert snake case string to camel snake
    :param value: Snake case string to convert
    :return: Camel case string
    """
    components = value.split('_')
    return (components[0] + ''.join(x.title() for x in components[1:])).title()


try:
    print('--------------------------------------------------------------------------------------------------')
    print('ECS Deployment Tool')
    print('--------------------------------------------------------------------------------------------------')
    print()

    # Validate GitHub workspace was configured
    if 'GITHUB_WORKSPACE' not in os.environ.keys():
        raise Exception('No GITHUB_WORKSPACE was specified, please ensure GITHUB_WORKSPACE environment variable has been set')

    # Change into the repository root folder
    os.chdir(os.environ['GITHUB_WORKSPACE'])

    # Validate required environment variables are set
    if 'ENVIRONMENT' not in os.environ.keys():
        raise Exception('No deployment environment was specified, please ensure ENVIRONMENT action variable has been set')

    # Validate the GitHub SHA was supplied
    if 'IMAGE_TAG' not in os.environ.keys():
        raise Exception('No ECR image tag was specified, please ensure IMAGE_TAG action variable has been set')

    # Load deployment configuration
    deployment_configuration_filename = '{path_repository_root}/.github/deploy.yml'.format(
        path_repository_root=GitHub.get_repository_root()
    )

    deployment_configuration = ConfigurationFile(deployment_configuration_filename)
    environment_id = os.environ['ENVIRONMENT']
    github_sha = os.environ['IMAGE_TAG']
    aws_account_id = deployment_configuration.get_aws_account_id(environment_id)
    deployment_containers = deployment_configuration.get_container_names(environment_id)
    repository_url = '{aws_account_id}.dkr.ecr.{aws_deployment_region}.amazonaws.com'.format(
        aws_account_id=deployment_configuration.get_aws_account_id(environment_id),
        aws_deployment_region=deployment_configuration.get_aws_deployment_region(environment_id)
    )

    # If a specific deployment container was specified, make sure it exists
    if 'DEPLOY_CONTAINER' in os.environ.keys():
        selected_container = os.environ['DEPLOY_CONTAINER']
        if selected_container not in deployment_containers:
            raise Exception('The requested container ({selected_container}) did not exist in the environment'.format(selected_container=selected_container))
        # Just truncate to the single container
        deployment_containers = [os.environ['DEPLOY_CONTAINER']]

    # Create 'docker-compose.yml' file for each container
    print('--------------------------------------------------------------------------------------------------')
    print('Creating Build Files')
    print('--------------------------------------------------------------------------------------------------')

    build_files = {}
    for container_id in deployment_containers:
        ecs_service_name = to_camel_case(container_id)
        build_files[container_id] = DockerCompose.create_build_file(
            context=GitHub.get_repository_root(),
            container_id=container_id,
            dockerfile=deployment_configuration.get_container_filename(environment_id, container_id),
            image='{repository_url}/{container_id}:{github_sha}'.format(
                repository_url=repository_url,
                container_id=container_id,
                github_sha=github_sha
            )
        )
        print('Created: {ecs_service_name} ({filename})'.format(
            ecs_service_name=ecs_service_name,
            filename=build_files[container_id]
        ))

    # Start building and deploying the containers
    # Build each container locally
    for container_id in deployment_containers:
        ecs_service_name = to_camel_case(container_id)
        print('--------------------------------------------------------------------------------------------------')
        print('Building {ecs_service_name} Docker Container'.format(ecs_service_name=ecs_service_name))
        print('--------------------------------------------------------------------------------------------------')
        stdout, stderr = DockerCompose.build(build_files[container_id])
        print()
        print(stdout)
        print()

    # Push each container to ECR repository
    print('--------------------------------------------------------------------------------------------------')
    print('Pushing Docker Containers To ECR')
    print('--------------------------------------------------------------------------------------------------')
    for container_id in deployment_containers:
        ecs_service_name = to_camel_case(container_id)
        print('Pushing: {ecs_service_name} ({repository_url})'.format(
            ecs_service_name=ecs_service_name,
            repository_url=repository_url
        ))
        Docker.login(
            repository_url=repository_url,
            username='AWS',
            password=AwsCli.ecr_get_login_password(deployment_configuration.get_aws_deployment_region(environment_id))
        )
        DockerCompose.push(build_files[container_id])

    # Update ECS services
    print('--------------------------------------------------------------------------------------------------')
    print('Updating ECS Containers')
    print('--------------------------------------------------------------------------------------------------')

    ecs_client = Ecs.Client()
    ssm_client = Ssm.Client()
    cloud_watch_client = CloudWatch.Client()
    ecs_cluster_name = deployment_configuration.get_aws_deployment_cluster_name(environment_id)
    ecs_task_definitions = {}
    ecs_service_rollbacks_required = []
    ecs_task_definition_rollbacks_required = []
    ssm_image_rollbacks_required = []

    # Validate the all required ECS services were found and retrieve the deployed task definition for each service
    ecs_services = ecs_client.get_services_by_name(cluster=ecs_cluster_name)
    for container_id in deployment_containers:
        ecs_service_name = to_camel_case(container_id)
        if ecs_service_name not in ecs_services.keys():
            raise Exception('Could not locate required ECS service ({ecs_service_name})'.format(ecs_service_name=ecs_service_name))
        # Store the existing task definition
        ecs_task_definitions[ecs_service_name] = ecs_client.get_task_definition(ecs_services[ecs_service_name]['taskDefinition'])

    try:
        for container_id in deployment_containers:
            ecs_service_name = to_camel_case(container_id)
            ecs_service = ecs_services[ecs_service_name]

            # Retrieve the original image URL
            original_image = None
            for container_definition in ecs_task_definitions[ecs_service_name]['containerDefinitions']:
                if container_definition['name'] == ecs_service_name:
                    original_image = container_definition['image']

            # If there is no existing image do not proceed
            if original_image is None:
                raise Exception('No existing image could be found for the service')

            # Construct new image name
            new_image = '{repository_url}/{container_id}:{github_sha}'.format(
                repository_url=repository_url,
                container_id=container_id.replace("_", "-"),
                github_sha=github_sha
            )

            # If the new and old images are the same, skip this update- nothing has changed
            if original_image == new_image:
                print('Updating: {ecs_service_name} (Skipped- Image Has Not Changed)'.format(ecs_service_name=ecs_service_name))
            else:
                print('Updating: {ecs_service_name}'.format(ecs_service_name=ecs_service_name))
                ecs_service_rollbacks_required.append(ecs_service_name)
                task_definition_arn = ecs_client.update_service_container(
                    cluster_name=ecs_cluster_name,
                    service_name=ecs_service_name,
                    container_name=ecs_service_name,
                    image=new_image
                )

                print('New Task Definition ARN: {task_definition_arn}'.format(task_definition_arn=task_definition_arn))
                ecs_task_definition_rollbacks_required.append(task_definition_arn)

                if deployment_configuration.is_wait_service_stable_required(environment_id=environment_id, container_id=container_id):
                    print('Waiting for service to stabilize: {ecs_service_name}'.format(ecs_service_name=ecs_service_name))
                    ecs_client.wait_services_stable(
                        cluster_name=ecs_cluster_name,
                        services=[ecs_service_name]
                    )

            # Regardless of whether the image has changed, always run the task if requested
            if deployment_configuration.is_container_run_required(environment_id=environment_id, container_id=container_id):

                print('Executing: {ecs_service_name}'.format(ecs_service_name=ecs_service_name))
                task_arns = ecs_client.run_task_from_service(
                    cluster_name=ecs_cluster_name,
                    service_name=ecs_service_name,
                    count=1
                )

                for task_arn in task_arns:
                    print('Executing Task ARN: {task_arn}'.format(task_arn=task_arn))

                if len(task_arns) > 0:
                    print('Waiting For Task To Finish: {ecs_service_name}'.format(ecs_service_name=ecs_service_name))
                    wait_result = ecs_client.wait_tasks_stopped(
                        cluster_name=ecs_cluster_name,
                        task_arns=task_arns
                    )

                    # Search for CloudWatch log output
                    print('--------------------------------------------------------------------------------------------------')
                    print('Execution Logs')
                    print('--------------------------------------------------------------------------------------------------')
                    try:
                        found = False
                        for container in ecs_task_definitions[ecs_service_name]['containerDefinitions']:
                            if container['name'] == ecs_service_name:
                                found = True
                                # Display the log output
                                log_group_name = container['logConfiguration']['options']['awslogs-group']
                                log_stream_prefix = container['logConfiguration']['options']['awslogs-stream-prefix']
                                events = cloud_watch_client.get_log_events(
                                    log_group_name=log_group_name,
                                    log_stream_prefix=log_stream_prefix,
                                    task_arn=task_arns[0]
                                )

                                for event in events:
                                    print('{timestamp}: {message}'.format(
                                        timestamp=datetime.fromtimestamp(event['timestamp'] / 1000),
                                        message=event['message']
                                    ))

                        if found is False:
                            raise Exception('Could not locate CloudWatch log configuration')
                    except Exception as exception:
                        print(exception)
                        print('WARNING: Failed to locate CloudWatch logs for the task. This is most likely caused by the ECS task failing to start- please refer to ECS stopped tasks lists for more information')
                    print('--------------------------------------------------------------------------------------------------')

                    # Retrieve the exit code for the container
                    task = ecs_client.get_task(
                        cluster_name=ecs_cluster_name,
                        task_arn=task_arns[0]
                    )

                    # Search for the container inside the task
                    found = False
                    for container in task['containers']:
                        if container['name'] == ecs_service_name:
                            found = True
                            if 'exitCode' in container.keys():
                                if container['exitCode'] != 0:
                                    raise Exception('Non-zero exit code ({exit_code}) returned from container'.format(
                                        exit_code=container['exitCode']
                                    ))
                            else:
                                raise Exception('No exit code found for container. This is most likely caused by the ECS task failing to start- please refer to ECS stopped tasks lists for more information')

                    # If we couldn't find the exit code, something went wrong
                    if found is False:
                        raise Exception('Could not locate expected container result in task description')
                else:
                    raise Exception('Failed to start task')

        # Update the SSM parameters used by Terraform with latest deployed tags
        print('--------------------------------------------------------------------------------------------------')
        print('Updating Terraform SSM Image Tags')
        print('--------------------------------------------------------------------------------------------------')
        for container_id in deployment_containers:
            ecs_service_name = to_camel_case(container_id)
            path = '/Terraform/ECS/Tag/{ecs_service_name}'.format(ecs_service_name=ecs_service_name)
            original_value = ssm_client.get_parameter(path=path)
            print('Updating: {path} ({original_value} => {github_sha})'.format(
                path=path,
                original_value=original_value,
                github_sha=github_sha
            ))
            ssm_image_rollbacks_required.append({
                "path": path,
                "value": original_value
            })
            ssm_client.put_parameter(
                path=path,
                value=github_sha,
                secure=False,
                allow_overwrite=True
            )

    except Exception as exception:
        # If there were an services that successfully updated, or where updated were attempted- roll them back
        if len(ecs_service_rollbacks_required) > 0:
            print('--------------------------------------------------------------------------------------------------')
            print('Rolling Back Containers')
            print('--------------------------------------------------------------------------------------------------')

            for ecs_service_name in ecs_service_rollbacks_required:
                # Roll back inside a try/except block to allow us to continue in the face of errors
                try:
                    original_image = None
                    for container_definition in ecs_task_definitions[ecs_service_name]['containerDefinitions']:
                        if container_definition['name'] == ecs_service_name:
                            original_image = container_definition['image']

                    # If there is no existing image do not proceed
                    if original_image is None:
                        raise Exception('Could not locate original image')

                    print('Rolling back "{ecs_service_name}" service image: {original_image}'.format(
                        ecs_service_name=ecs_service_name,
                        original_image=original_image
                    ))
                    ecs_client.update_service_container(
                        cluster_name=ecs_cluster_name,
                        service_name=ecs_service_name,
                        container_name=ecs_service_name,
                        image=original_image
                    )
                except Exception as exception_rollback:
                    print('FATAL ERROR: Rollback failed with exception error- attempting to continue rollback')
                    print(exception_rollback)

        # If there were an services that successfully updated, or where updated were attempted- roll them back
        if len(ecs_task_definition_rollbacks_required) > 0:
            print('--------------------------------------------------------------------------------------------------')
            print('Deregistering Task Definitions')
            print('--------------------------------------------------------------------------------------------------')

            for task_definition_arn in ecs_task_definition_rollbacks_required:
                print('Deregistering: {task_definition_arn}'.format(task_definition_arn=task_definition_arn))
                ecs_client.deregister_task_definition(task_definition_arn=task_definition_arn)

        if len(ssm_image_rollbacks_required) > 0:
            print('--------------------------------------------------------------------------------------------------')
            print('Rolling Back Terraform SSM Image Tags')
            print('--------------------------------------------------------------------------------------------------')
            for ssm_image in ssm_image_rollbacks_required:
                print('Reverting: {path}'.format(path=ssm_image['path']))
                ssm_client.put_parameter(
                    path=ssm_image["path"],
                    value=ssm_image["value"],
                    secure=False,
                    allow_overwrite=True
                )

        raise Exception(exception)

except Exception as exception:
    print('FATAL ERROR: {exception}'.format(exception=exception))
    exit(1)
#!/usr/bin/env python3
import os
from datetime import datetime

from Aws.Clients import CloudWatch, Ecs, Ssm
from typing import Optional, Dict


def to_camel_case(value: str) -> str:
    """
    Convert snake case string to camel snake
    :param value: Snake case string to convert
    :return: Camel case string
    """
    components = value.split('_')
    return (components[0] + ''.join(x.title() for x in components[1:])).title()


# Validate required environment variables are set
if 'ENVIRONMENT' not in os.environ.keys():
    raise Exception('No deployment environment was specified, please ensure ENVIRONMENT environment variable has been set')
if 'ECS_CLUSTER_NAME' not in os.environ.keys():
    raise Exception('No ECS cluster name was specified, please ensure ECS_CLUSTER_NAME environment variable has been set')
if 'ECS_TASK_NAME' not in os.environ.keys():
    raise Exception('No ECS task name was specified, please ensure ECS_TASK_NAME environment variable has been set')
if 'ECS_SERVICE_NAME' not in os.environ.keys():
    raise Exception('No ECS service name was specified, please ensure ECS_SERVICE_NAME environment variable has been set')
if 'IMAGE_TAG' not in os.environ.keys():
    raise Exception('No docker image tag specified, please ensure IMAGE_TAG environment variable has been set')

ecs_client = Ecs.Client()
ssm_client = Ssm.Client()
cloud_watch_client = CloudWatch.Client()
ecs_cluster_name = os.environ['ECS_CLUSTER_NAME']
ecs_task_name = os.environ['ECS_TASK_NAME']
ecs_service_name = os.environ['ECS_SERVICE_NAME']
run_task = os.environ['RUN_TASK'].lower().strip() in ['1', 'true', 'yes', 'y'] if 'RUN_TASK' in os.environ.keys() else False
image_tag = os.environ['IMAGE_TAG']
environment = os.environ['ENVIRONMENT']

print('------------------------------------------------------------------------------------------')
print('Beginning deployment')
print('------------------------------------------------------------------------------------------')

# Change into the repository root folder
os.chdir(os.environ['GITHUB_WORKSPACE'])

# Get the ECS task definition for the requested cluster/service/task
task_definition_arns = ecs_client.list_task_definitions_by_service_name()

# Get the ECS service for the requested cluster/service/task
ecs_services = ecs_client.get_services_by_name(cluster=ecs_cluster_name)
found_version: int = 0
ecs_service: Optional[Dict] = None
ecs_service_name_found: Optional[str] = None
for key, value in ecs_services.items():
    # If the service name is an exact match, use it
    if key.lower() == ecs_service_name.lower():
        ecs_service = value
        ecs_service_name_found = key
        break
    # Otherwise this is a kludge for the way that Harness names its tasks with an incrementing number (e.g. 'Api__102')
    if key.lower().startswith(ecs_task_name.lower()):
        key_split = key.lower().split('__')
        if len(key_split) == 2:
            if key_split[0] == ecs_service_name.lower() and key_split[1].isnumeric():
                if int(key_split[1]) > found_version:
                    found_version = int(key_split[1])
                    ecs_service = value
                    ecs_service_name_found = key

if ecs_service is None:
    raise Exception(f'Could not locate the requested ECS service: {ecs_service_name}. Please contact the DevOps team to resolve this issue.')

if ecs_task_name not in task_definition_arns.keys():
    raise Exception(f'Could not locate requested ECS task definition: {ecs_task_name}. Please contact the DevOps team to resolve this issue.')
try:
    ecs_task_definition = ecs_client.get_task_definition(task_definition_arns[ecs_task_name])
except Exception as exception:
    raise Exception(f'Could not locate ECS task definition for requested service: {ecs_service_name}. Please contact the DevOps team to resolve this issue.')

# Retrieve the original image URL
original_image = None
for container_definition in ecs_task_definition['containerDefinitions']:
    if container_definition['name'].lower() == ecs_task_name.lower():
        original_image = container_definition['image']

# If there is no existing image do not proceed
if original_image is None:
    raise Exception(f'Could not locate currently deployed image name for ECS service: {ecs_service_name}. Please contact the DevOps team to resolve this issue.')

# Create new image name
original_image_split_slash = original_image.split('/')
original_image_split_colon = original_image_split_slash[1].split(':')
new_image = f'{original_image_split_slash[0]}/{original_image_split_colon[0]}:{image_tag}'

rollback_required = False
try:
    # If the new and old images are the same, skip this update- nothing has changed
    if original_image == new_image and False:
        print(f'Container image has not changed since last deployment. No changes have been made.')
        exit(1)
    else:
        rollback_required = True
        task_definition_arn = ecs_client.update_service_container(
            cluster_name=ecs_cluster_name,
            service_name=ecs_service_name,
            container_name=ecs_task_name,
            task_definition_arn=ecs_task_definition['taskDefinitionArn'],
            image=new_image
        )

        print('Original container image: {original_image}'.format(original_image=original_image))
        print('New container image: {new_image}'.format(new_image=new_image))
        print('New Task Definition ARN: {task_definition_arn}'.format(task_definition_arn=task_definition_arn))
        print('Waiting for service to stabilize: {ecs_service_name}'.format(ecs_service_name=ecs_service_name))

        ecs_client.wait_services_stable(cluster_name=ecs_cluster_name, services=[ecs_service_name])
        print('Service stabilized')

        # Search for CloudWatch log output
        service_task_arns = ecs_client.list_running_task_arns(
            cluster_name=ecs_cluster_name,
            service_name=ecs_service_name
        )
        for task_arn in service_task_arns:
            print('------------------------------------------------------------------------------------------')
            print(f'Container startup logs: {task_arn}')
            print('------------------------------------------------------------------------------------------')
            for container in ecs_task_definition['containerDefinitions']:
                if container['name'].lower() == ecs_task_name.lower():
                    found = True
                    # Display the log output
                    log_group_name = container['logConfiguration']['options']['awslogs-group']
                    log_stream_prefix = container['logConfiguration']['options']['awslogs-stream-prefix']
                    events = cloud_watch_client.get_log_events(
                        log_group_name=log_group_name,
                        log_stream_prefix=to_camel_case(log_stream_prefix),
                        task_arn=task_arn
                    )
                    for event in events:
                        print('{timestamp}: {message}'.format(
                            timestamp=datetime.fromtimestamp(event['timestamp'] / 1000),
                            message=event['message']
                        ))

        # Regardless of whether the image has changed, always run the task if requested
        if run_task is True:
            print('------------------------------------------------------------------------------------------')
            print('Running: {ecs_service_name}'.format(ecs_service_name=ecs_service_name))
            print('------------------------------------------------------------------------------------------')
            running_task_arns = ecs_client.run_task_from_service(
                cluster_name=ecs_cluster_name,
                service_name=ecs_service_name,
                count=1
            )
            for task_arn in running_task_arns:
                print('Executing Task ARN: {task_arn}'.format(task_arn=task_arn))

            if len(running_task_arns) > 0:
                print('Waiting For Tasks To Finish: {ecs_service_name}'.format(ecs_service_name=ecs_service_name))
                wait_result = ecs_client.wait_tasks_stopped(
                    cluster_name=ecs_cluster_name,
                    task_arns=running_task_arns
                )

                for task_arn in running_task_arns:
                    print('------------------------------------------------------------------------------------------')
                    print(f'Execution logs: {task_arn}')
                    print('------------------------------------------------------------------------------------------')
                    for container in ecs_task_definition['containerDefinitions']:
                        if container['name'].lower() == ecs_task_name.lower():
                            found = True
                            # Display the log output
                            log_group_name = container['logConfiguration']['options']['awslogs-group']
                            log_stream_prefix = container['logConfiguration']['options']['awslogs-stream-prefix']
                            events = cloud_watch_client.get_log_events(
                                log_group_name=log_group_name,
                                log_stream_prefix=to_camel_case(log_stream_prefix),
                                task_arn=task_arn
                            )
                            for event in events:
                                print('{timestamp}: {message}'.format(
                                    timestamp=datetime.fromtimestamp(event['timestamp'] / 1000),
                                    message=event['message']
                                ))

                # Retrieve the exit code for the container
                task = ecs_client.get_task(
                    cluster_name=ecs_cluster_name,
                    task_arn=running_task_arns[0]
                )

                # Search for the container inside the task
                found = False
                for container in task['containers']:
                    if container['name'] == ecs_service_name:
                        found = True
                        if 'exitCode' in container.keys():
                            if container['exitCode'] != 0:
                                raise Exception(f'Non-zero exit code ({container["exitCode"]}) returned from container')
                        else:
                            raise Exception('No exit code found for container. This is most likely caused by the ECS task failing to start- please refer to ECS stopped tasks lists for more information')

                # If we couldn't find the exit code, something went wrong
                if found is False:
                    raise Exception('Could not locate expected container result in task description')
            else:
                raise Exception('Failed to start task')

except Exception as exception:
    print('------------------------------------------------------------------------------------------')
    print('Exception error')
    print('------------------------------------------------------------------------------------------')
    print(exception)

    if rollback_required is True:
        print('------------------------------------------------------------------------------------------')
        print('Rolling back service definition')
        print('------------------------------------------------------------------------------------------')
        task_definition_arn=ecs_client.update_service_container(
            cluster_name=ecs_cluster_name,
            service_name=ecs_service_name,
            container_name=ecs_service_name,
            task_definition_arn=ecs_task_definition['taskDefinitionArn'],
            image=original_image
        )

        print('Rollback container image: {original_image}'.format(original_image=original_image))
        print('Rollback Task Definition ARN: {task_definition_arn}'.format(task_definition_arn=task_definition_arn))
        print('Waiting for service to stabilize: {ecs_service_name}'.format(ecs_service_name=ecs_service_name))
        ecs_client.wait_services_stable(cluster_name=ecs_cluster_name, services=[ecs_service_name])
        print('Service stabilized, rollback completed successfully')

    exit(1)

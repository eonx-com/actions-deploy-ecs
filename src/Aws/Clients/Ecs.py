from typing import Dict, Optional, List, Any

from Aws.Client import Client as BaseClient
from Aws.Session import Session


class Client(BaseClient):
    def __init__(self, session: Session = None):
        """
        Configure ECS client
        """
        super().__init__(session=session, client='ecs')

    def get_services_by_name(self, cluster: str) -> Dict:
        """
        Retrieve a list of all ECS services in a cluster
        :param cluster: The ECS cluster name
        :return: Dictionary of ECS services indexed by the service name
        """
        return self.__get_services__(cluster_name=cluster, index='serviceName')

    def get_service_by_name(self, cluster: str, name: str) -> Optional[Dict]:
        """
        Retrieve a list of all ECS services in a cluster
        :param cluster: The ECS cluster name
        :param name: The ECS service name
        :return: ECS service or None if not found
        """
        services = self.__get_services__(cluster_name=cluster, index='serviceName')
        if name in services.keys():
            return services[name]
        return None

    def get_services_by_arn(self, cluster: str) -> Dict:
        """
        Retrieve a list of all ECS services in a cluster
        :param cluster: The ECS cluster name
        :return: Dictionary of ECS services indexed by their ARN
        """
        return self.__get_services__(cluster_name=cluster, index='serviceArn')

    def get_task_definition(self, arn: str) -> Dict[str, str]:
        """
        Retrieve task definition by its ARN
        :param arn: The ARN of the task definition to retrieve
        :return: Task definition
        """
        describe_task_definition_result = self.get_client().describe_task_definition(
            taskDefinition=arn,
            include=['TAGS']
        )
        return describe_task_definition_result['taskDefinition']

    def list_task_definitions_by_service_name(self) -> Dict[str, str]:
        """
        Return a list of task definitions indexed by the service name
        :return: Dictionary of task definition ARNs indexed by service name
        """
        task_definition_arns = self.list_task_definitions()

        task_definitions = {}

        for task_definition_arn in task_definition_arns:
            slash_split = str(task_definition_arn).split('/')
            colon_split = str(slash_split[1]).split(':')
            service_name = colon_split[0]
            # If the service isn't already found- add it. Otherwise skip it as the later definitions will be older (as they are sorted in descending order)
            if service_name not in task_definitions.keys():
                task_definitions[service_name] = task_definition_arn

        return task_definitions

    def list_task_definitions(self) -> List[str]:
        """
        Return a list of task definitions
        :return: List of task definition ARNs
        """
        list_task_definition_result = self.get_client().list_task_definitions(
            status='ACTIVE',
            sort='DESC'
        )

        task_definition_arns = []

        while True:
            task_definition_arns.extend(list_task_definition_result['taskDefinitionArns'])

            # If there are no more results, get out of here
            if 'nextToken' not in list_task_definition_result:
                break

            # Load next page of results
            list_task_definition_result = self.get_client().list_task_definitions(
                status='ACTIVE',
                sort='DESC',
                nextToken=list_task_definition_result['nextToken']
            )

        return task_definition_arns

    def run_task_from_service(self, cluster_name: str, service_name: str, count: int = 1) -> List[str]:
        """
        Run an ECS task from a service definition
        :param cluster_name: The ECS cluster name
        :param service_name: ECS service to use
        :param count: Number of task to run
        :return: List of task ARNs
        """
        ecs_service = self.get_service_by_name(
            cluster=cluster_name,
            name=service_name
        )
        run_task_result = self.get_client().run_task(
            cluster=cluster_name,
            count=count,
            enableECSManagedTags=ecs_service['enableECSManagedTags'],
            launchType=ecs_service['launchType'],
            networkConfiguration=ecs_service['networkConfiguration'],
            placementConstraints=ecs_service['placementConstraints'],
            placementStrategy=ecs_service['placementStrategy'],
            platformVersion=ecs_service['platformVersion'],
            taskDefinition=ecs_service['taskDefinition']
        )

        tasks = []
        for task in run_task_result['tasks']:
            tasks.append(task['taskArn'])

        return tasks

    def get_task(self, cluster_name: str, task_arn: str) -> Dict:
        """
        Retrieve task description
        :param cluster_name: ECS cluster name
        :param task_arn: ECS task ARN
        :return: Task description
        """
        describe_tasks_result = self.get_client().describe_tasks(
            cluster=cluster_name,
            tasks=[task_arn],
            include=['TAGS']
        )
        return describe_tasks_result['tasks'][0]

    def wait_tasks_running(self, cluster_name: str, task_arns: List[str], delay=20, max_attempts=9) -> Any:
        """
        Wait for the listed tasks to start running
        :param cluster_name: The ECS cluster name
        :param task_arns: List of task ARNs
        :param delay: Number of seconds to wait between checks
        :param max_attempts: Maximum number of attempts to be made
        """
        waiter = self.get_client().get_waiter('tasks_running')
        return waiter.wait(
            cluster=cluster_name,
            tasks=task_arns,
            include=['TAGS'],
            WaiterConfig={
                'Delay': delay,
                'MaxAttempts': max_attempts
            }
        )

    def wait_tasks_stopped(self, cluster_name: str, task_arns: List[str], delay=20, max_attempts=9) -> Any:
        """
        Wait for the listed tasks to stop running
        :param cluster_name: The ECS cluster name
        :param task_arns: List of task ARNs
        :param delay: Number of seconds to wait between checks
        :param max_attempts: Maximum number of attempts to be made
        """
        waiter = self.get_client().get_waiter('tasks_stopped')
        return waiter.wait(
            cluster=cluster_name,
            tasks=task_arns,
            include=['TAGS'],
            WaiterConfig={
                'Delay': delay,
                'MaxAttempts': max_attempts
            }
        )

    def wait_services_stable(self, cluster_name: str, services: List[str], delay=20, max_attempts=18) -> Any:
        """
        Wait for the listed services to stabilize
        :param cluster_name: The ECS cluster name
        :param services: The ECS services
        :param delay: Number of seconds to wait between checks
        :param max_attempts: Maximum number of attempts to be made
        """
        waiter = self.get_client().get_waiter('services_stable')
        return waiter.wait(
            cluster=cluster_name,
            services=services,
            include=['TAGS'],
            WaiterConfig={
                'Delay': delay,
                'MaxAttempts': max_attempts
            }
        )

    def wait_services_inactive(self, cluster_name: str, services: List[str], delay=20, max_attempts=9) -> None:
        """
        Wait for the listed services to be inactive
        :param cluster_name: The ECS cluster name
        :param services: The ECS services
        :param delay: Number of seconds to wait between checks
        :param max_attempts: Maximum number of attempts to be made
        """
        waiter = self.get_client().get_waiter('services_inactive')
        return waiter.wait(
            cluster=cluster_name,
            services=services,
            include=['TAGS'],
            WaiterConfig={
                'Delay': delay,
                'MaxAttempts': max_attempts
            }
        )

    def __get_services__(self, cluster_name: str, index: str) -> Optional[Dict]:
        """
        Retrieve a list of all ECS services in a cluster and index by the selected field
        :param cluster_name: The ECS cluster name
        :param index: The field to use as the dictionary index
        :return: Dictionary of ECS services indexed by the selected field
        """
        services = {}
        service_arns = []

        list_services_result = self.get_client().list_services(cluster=cluster_name)

        while True:
            for service_arn in list_services_result['serviceArns']:
                service_arns.append(service_arn)
            # If there are no further results, get out of here now
            if 'nextToken' not in list_services_result.keys():
                break
            # Retrieve next page of results
            list_services_result = self.get_client().list_services(
                cluster=cluster_name,
                nextToken=list_services_result['nextToken']
            )

        # Return empty list now if we didn't find any service ARNs
        if len(service_arns) == 0:
            return None

        describe_services_result = self.get_client().describe_services(
            cluster=cluster_name,
            services=service_arns,
            include=['TAGS']
        )

        # Break the service ARN list into chunks of 10 (maximum supported by describe service method)
        service_arn_chunks = BaseClient.__chunk_list__(source=service_arns, size=10)

        # Pass each chunk in and describe all the services we found
        for service_arns in service_arn_chunks:
            describe_services_result = self.get_client().describe_services(
                cluster=cluster_name,
                services=service_arns,
                include=['TAGS']
            )
            for service in describe_services_result['services']:
                services[service[index]] = service

        return services

    def deregister_task_definition(self, task_definition_arn: str):
        """
        Deregister a task definition
        :param task_definition_arn: Task definition ARN
        """
        self.get_client().deregister_task_definition(
            taskDefinition=task_definition_arn
        )

    def update_service_container(
            self,
            cluster_name: str,
            service_name: str,
            container_name: str,
            image: str,
            task_definition_arn: str,
            entrypoint: Optional[Dict] = None,
            command: Optional[Dict] = None
    ) -> str:
        """
        Update a container in an ECS service definition to point to a new ECR image
        :param cluster_name: ECS cluster name
        :param service_name: ECS service name
        :param container_name: Container to be updated
        :param image: ECR image URL
        :param entrypoint: Optional entrypoint override
        :param task_definition_arn: The new task definition ARN
        :param command: Optional command override
        :return: The updated ECS task definition ARN
        """
        ecs_service = self.get_service_by_name(
            cluster=cluster_name,
            name=service_name
        )

        # Retrieve the existing task definition
        task_definition = self.get_task_definition(task_definition_arn)

        # Update the image in the task definition
        task_definition['image'] = image

        # Update the image of the specified container
        for container_definition in task_definition['containerDefinitions']:
            if container_definition['name'] == container_name:
                container_definition['image'] = image
                # If an entrypoint override was specified, set it here
                if entrypoint is not None:
                    container_definition['entryPoint'] = entrypoint
                # If a command override was specified, set it here
                if command is not None:
                    container_definition['command'] = command

        # Register a new task definition
        register_task_definition_result = self.get_client().register_task_definition(
            family=task_definition['family'],
            taskRoleArn=task_definition['taskRoleArn'],
            executionRoleArn=task_definition['executionRoleArn'],
            networkMode=task_definition['networkMode'],
            containerDefinitions=task_definition['containerDefinitions'],
            volumes=task_definition['volumes'],
            placementConstraints=task_definition['placementConstraints'],
            requiresCompatibilities=task_definition['requiresCompatibilities'],
            cpu=task_definition['cpu'],
            memory=task_definition['memory']
        )

        if 'healthCheckGracePeriodSeconds' in ecs_service.keys():
            update_service_result = self.get_client().update_service(
                cluster=cluster_name,
                service=service_name,
                desiredCount=ecs_service['desiredCount'],
                taskDefinition=register_task_definition_result['taskDefinition']['taskDefinitionArn'],
                deploymentConfiguration=ecs_service['deploymentConfiguration'],
                networkConfiguration=ecs_service['networkConfiguration'],
                platformVersion=ecs_service['platformVersion'],
                forceNewDeployment=True,
                healthCheckGracePeriodSeconds=ecs_service['healthCheckGracePeriodSeconds']
            )
        else:
            update_service_result = self.get_client().update_service(
                cluster=cluster_name,
                service=service_name,
                desiredCount=ecs_service['desiredCount'],
                taskDefinition=register_task_definition_result['taskDefinition']['taskDefinitionArn'],
                deploymentConfiguration=ecs_service['deploymentConfiguration'],
                networkConfiguration=ecs_service['networkConfiguration'],
                platformVersion=ecs_service['platformVersion'],
                forceNewDeployment=True
            )

        return register_task_definition_result['taskDefinition']['taskDefinitionArn']

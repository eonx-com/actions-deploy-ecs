from Aws.Client import Client as BaseClient
from Aws.Session import Session
from typing import List


# noinspection DuplicatedCode
class Client(BaseClient):
    def __init__(self, session: Session = None):
        """
        Configure ECS client
        """
        super().__init__(session=session, client='logs')

    def get_log_events(self, log_group_name: str, log_stream_prefix: str, task_arn: str) -> List:
        """
        Return all log events
        :param log_group_name: CloudWatch log group name
        :param log_stream_prefix: CloudWatch log stream prefix
        :param task_arn: ECS task ARN
        :return: Log events
        """
        events = []

        task_id = task_arn.split('/')[2]
        log_stream_name = f'{log_group_name}/{log_stream_prefix}/{task_id}'
        print(f'Searching for log stream: {log_stream_name}')

        # Retrieve all events from the log stream
        get_log_events_result = self.get_client().get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )

        while True:
            for event in get_log_events_result['events']:
                events.append(event)

            # If there are no more events, get out of here now
            if 'nextToken' not in get_log_events_result.keys():
                break

            # Get next page of results
            get_log_events_result = self.get_client().get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                nextToken=get_log_events_result['nextForwardToken']
            )

        return events

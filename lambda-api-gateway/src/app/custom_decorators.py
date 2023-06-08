from fastapi import Request
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from aws_lambda_powertools.metrics import MetricUnit

def get_event(request: Request):
    return APIGatewayProxyEventV2(request.scope['aws.event'])

def moobar():
  print("hi")

def metrics_log_metrics(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if not request:
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
        if not request:
            raise Exception("Request object not found in arguments")

        event = APIGatewayProxyEventV2(request.scope['aws.event'])
        metrics.add_metric(name="SuccessfulBooking", unit=MetricUnit.Count, value=1)
        result = await func(*args, **kwargs)
        metrics.log_metrics()
        return result
    return wrapper

def logger_inject_lambda_context(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if not request:
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
        if not request:
            raise Exception("Request object not found in arguments")

        event = APIGatewayProxyEventV2(request.scope['aws.event'])
        logger.info(event)
        logger.structure_logs(append=True, method=event.request_context.http.method, path=event.request_context.http.path)
        return await func(*args, **kwargs)
    return wrapper

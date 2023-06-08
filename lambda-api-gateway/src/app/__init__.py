from fastapi import FastAPI, Query, Request, Depends
from mangum import Mangum
from aws_lambda_powertools import Logger
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2
from aws_lambda_powertools.metrics import MetricUnit
from pydantic import BaseModel, Field
import functools
from starlette.requests import Request

# TODO - figure out how to get import to work
from .custom_decorators import get_event, logger_inject_lambda_context, metrics_log_metrics
tracer = Tracer()
logger = Logger()
metrics = Metrics()
app = FastAPI()

class Transaction(BaseModel):
    id: int = Field(..., example=1)
    name: str = Field(..., example="buy apple")
    value: float = Field(..., example=1000.00)

transactions = []

metrics = Metrics()


######  Custom Decorators
# def get_event(request: Request):
#     return APIGatewayProxyEventV2(request.scope['aws.event'])
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
######################
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




@app.post("/transaction/")
# @logger.inject_lambda_context
@logger_inject_lambda_context
# @metrics.log_metrics
@metrics_log_metrics
@tracer.capture_method(capture_response=False                   )
async def create_transaction(request: Request, transaction: Transaction):
    event = get_event(request)
    logger.structure_logs(append=True, method=event.request_context.http.method, path=event.request_context.http.path)
    logger.info(f"Creating transaction with id {transaction.id}")
    transactions.append(transaction)
    tracer.put_annotation(key="transaction_id", value=transaction.id)
    metrics.add_metric(name="TransactionsCreated", unit=MetricUnit.Count, value=1)
    logger.info(f"Transaction created successfully {transaction.id}")
    transactions.append(transaction)
    return transaction


@app.get("/transaction/{transaction_id}")
@tracer.capture_method
# @logger.inject_lambda_context
@logger_inject_lambda_context
# @metrics.log_metrics
@metrics_log_metrics
async def read_transaction(request: Request, transaction_id: int):
    event = get_event(request)
    logger.structure_logs(append=True, method=event.request_context.http.method, path=event.request_context.http.path)
    logger.info(f"Fetching transaction with id {transaction_id}")
    for transaction in transactions:
        if transaction.id == transaction_id:
            return transaction
    return {"error": f"Transaction not found {transaction_id}"}

@app.put("/transaction/{transaction_id}")
@tracer.capture_method
# @logger.inject_lambda_context
@logger_inject_lambda_context
# @metrics.log_metrics
@metrics_log_metrics
async def update_transaction(transaction_id: int, transaction: Transaction, request: Request):
    event = get_event(request)
    logger.structure_logs(append=True, method=event.request_context.http.method, path=event.request_context.http.path)
    logger.info(f"Updating transaction with id {transaction_id}")
    for index, current_transaction in enumerate(transactions):
        if current_transaction.id == transaction_id:
            transactions[index] = transaction
            metrics.add_metric(name="TransactionsUpdated", unit=MetricUnit.Count, value=1)
            return {"message": "Transaction updated successfully"}
    return {"error": f"Transaction not found: {transaction_id}"}

@app.delete("/transaction/{transaction_id}")
@tracer.capture_method
# @logger.inject_lambda_context
@logger_inject_lambda_context
# @metrics.log_metrics
@metrics_log_metrics
async def delete_transaction(transaction_id: int, request: Request):
    event = get_event(request)
    logger.structure_logs(append=True, method=event.request_context.http.method, path=event.request_context.http.path)
    logger.info(f"Deleting transaction with id {transaction_id}")
    tracer.put_annotation(key="transaction_id", value=transaction_id)
    for index, current_transaction in enumerate(transactions):
        if current_transaction.id == transaction_id:
            transactions.pop(index)
            metrics.add_metric(name="TransactionsDeleted", unit=MetricUnit.Count, value=1)
            return {"message": "Transaction deleted successfully"}
    return {"error": f"Transaction not found {transaction_id}"}

@app.get("/transaction/list/")
@tracer.capture_method
# @logger.inject_lambda_context
@logger_inject_lambda_context
# @metrics.log_metrics
@metrics_log_metrics
async def list_transactions(request: Request, search: str = Query(None, max_length=20)):
    event = get_event(request)
    logger.structure_logs(append=True, method=event.request_context.http.method, path=event.request_context.http.path)
    logger.info(f"Listing transactions")
    if search:
        return [transaction for transaction in transactions if search in transaction.name]
    return transactions

@tracer.capture_method
@app.get("/")
def get_root():
    # adding custom metrics
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/metrics/
    metrics.add_metric(name="HelloWorldInvocations", unit=MetricUnit.Count, value=1)

    # structured log
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/logger/
    logger.info("Hello world API - HTTP 200")
    return {"message": "hello world"}

handler = Mangum(app)


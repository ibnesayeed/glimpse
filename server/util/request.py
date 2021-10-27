import logging
import os
from functools import wraps
from flask import jsonify, request

from mediacloud.error import MCException

logger = logging.getLogger(__name__)


def validate_params_exist(form, params):
    for param in params:
        if param not in form:
            raise ValueError('Missing required value for '+param)


def json_error_response(message, status_code=400):
    response = jsonify({
        'statusCode': status_code,
        'message': message,
    })
    response.status_code = status_code
    return response


def filters_from_args(request_args):
    """
    Helper to centralize reading filters from url params
    """
    timespans_id = safely_read_arg('timespanId')
    snapshots_id = safely_read_arg('snapshotId')
    foci_id = safely_read_arg('focusId')
    q = request_args['q'] if ('q' in request_args) and (request_args['q'] != 'undefined') else None
    return snapshots_id, timespans_id, foci_id, q


def arguments_required(*expected_args):
    """
    Handy decorator for ensuring that request params exist
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                logger.debug(request.args)
                validate_params_exist(request.args, expected_args)
                return func(*args, **kwargs)
            except ValueError as e:
                logger.exception("Missing a required arg")
                return json_error_response(e.args[0])
        return wrapper
    return decorator


def argument_is_valid(argument, valid_values):
    """
    Handy decorator for ensuring that the parameter is one of the valid values
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(request.args)
            is_valid = request.args[argument] in valid_values
            if not is_valid:
                return json_error_response('"{}" is not in {}'.format(argument, valid_values))
            return func(*args, **kwargs)
        return wrapper
    return decorator


def form_fields_required(*expected_form_fields):
    """
    Handy decorator for ensuring that the form has the fields you need
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                logger.debug(request.form)
                validate_params_exist(request.form, expected_form_fields)
                return func(*args, **kwargs)
            except ValueError as e:
                logger.exception("Missing a required form field")
                return json_error_response(e.args[0])
        return wrapper
    return decorator


def api_error_handler(func):
    """
    Handy decorator that catches any exception from the Media Cloud API and
    sends it back to the browser as a nicely formatted JSON error.  The idea is
    that the client code can catch these at a low level and display error messages.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MCException as e:
            logger.exception(e)
            return json_error_response(e.message, e.status_code)
    return wrapper


def is_csv(filename):
    filename, file_extension = os.path.splitext(filename)
    return file_extension.lower() in ['.csv']


def csv_required(func):
    """
    Validates a file is supplied in the request and that it has a csv extension.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if 'file' not in request.files:
                return json_error_response('No file part')
            uploaded_file = request.files['file']
            if uploaded_file.filename == '':
                return json_error_response('No selected file')
            if not (uploaded_file and is_csv(uploaded_file.filename)):
                return json_error_response('Invalid file')
            return func(*args, **kwargs)
        except MCException as e:
            logger.exception(e)
            return json_error_response(e.message, e.status_code)
    return wrapper


def safely_read_arg(arg_name, default=None):
    return request.args[arg_name] if arg_name in request.args else default

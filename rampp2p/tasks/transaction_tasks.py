from celery import shared_task
from typing import Dict
from decimal import Decimal
from django.conf import settings

from rampp2p import utils
from rampp2p.utils.websocket import send_order_update, send_market_price
from rampp2p.serializers import TransactionSerializer, RecipientSerializer
from rampp2p.models import (
    Transaction, 
    StatusType, 
    Contract
)

import subprocess
import json
import re

import logging
logger = logging.getLogger(__name__)

@shared_task(queue='rampp2p__contract_execution')
def execute_subprocess(command):
    # execute subprocess
    logger.warning(f'executing: {command}')
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate() 

    stderr = stderr.decode("utf-8")
    stdout = stdout.decode('utf-8')
    # logger.warning(f'stdout: {stdout}, stderr: {stderr}')

    if stdout is not None:
        # Define the pattern for matching control characters
        control_char_pattern = re.compile('[\x00-\x1f\x7f-\x9f]')
        
        # Remove all control characters from the JSON string
        clean_stdout = control_char_pattern.sub('', stdout)

        stdout = json.loads(clean_stdout)
    
    response = {'result': stdout, 'error': stderr} 
    # logger.warning(f'response: {response}')

    return response

@shared_task(queue='rampp2p__subprocess_execution')
def rates_handler(rates, currency):
    logger.warn(f'rates: {rates}')
    logger.warn(f'currency: {currency}')
    send_market_price(rates)

@shared_task(queue='rampp2p__contract_execution')
def verify_tx_out(data: Dict, **kwargs):
    '''
    Verifies if transaction details (input, outputs, and amounts) satisfy the prerequisites of its contract.
    Automatically updates the order's status if transaction is valid and sends the result through a websocket channel.
    '''

    # Logs for debugging
    logger.warning(f'data: {data}')
    # logger.warning(f'kwargs: {kwargs}')

    valid = True
    error_msg = ""
    action = kwargs.get('action')

    # transaction must have at least 1 confirmation
    confirmations = data.get('result').get('confirmations')
    min_req_confirmations = 1
    if confirmations != None and confirmations < min_req_confirmations:
        error = {"error": f"transaction needs to have at least {min_req_confirmations} confirmations."}
        return send_order_update(
            error,
            contract.order.id
        )
    
    tx_inputs = data.get('result').get('inputs')
    tx_outputs = data.get('result').get('outputs')

    contract = Contract.objects.get(pk=kwargs.get('contract_id'))

    # The transaction is invalid, if inputs or outputs are empty
    if tx_inputs is None or tx_outputs is None:
        error = data.get('result').get('error')
        return send_order_update(
            error,
            contract.order.id
        )
    
    outputs = []
    if action == Transaction.ActionType.ESCROW:
        '''
        If the transaction is ActionType.ESCROW (transaction that is required to update status
        from ESCROW_PENDING to ESCROWED) the transaction's:
            (1) output amount must be correct, and 
            (2) output address must be the contract address.
        '''
        fees = utils.get_contract_fees()
        amount = contract.order.crypto_amount + fees

        # Find the output where address = contract address
        match_amount = None
        for output in tx_outputs:
            address = output.get('address')

            if address == contract.contract_address:
                # Convert amount value to decimal (8 decimal places)
                match_amount = Decimal(output.get('amount'))
                match_amount = match_amount.quantize(Decimal('0.00000000'))

                outputs.append({
                    "address": address,
                    "amount": str(match_amount)
                })
                break

        # Check if the amount is correct
        if match_amount != amount:
            valid = False
    
    else:
        '''
        If the transaction is for ActionType.RELEASE or ActionType.REFUND (transactions that are required
        to move from status RELEASE_PENDING to RELEASED or REFUND_PENDING to REFUNDED), the transaction's:
            (1) input address must be the contract address,
            (2) outputs must include the:
                (i)   servicer address with correct trading fee,
                (ii)  arbiter address with correct arbitration fee,
                (iii) buyer (if RELEASE) or seller (if REFUND) address with correct amount minus fees.
        '''
        # Find the contract address in the list of transaction's inputs
        sender_is_contract = False
        for input in tx_inputs:
            address = input.get('address')
            if address == contract.contract_address:
                sender_is_contract = True
                break
        
        # Set valid=False if contract address is not in transaction inputs and return
        if sender_is_contract == False:
            result = {
                "success": False,
                "error": "contract address not found in tx inputs"
            }
            # Send result through websocket
            return send_order_update(
                result, 
                contract.order.id
            )
        
        # Retrieve expected transaction output addresses
        arbiter, buyer, seller, servicer = utils.get_order_peer_addresses(contract.order)

        # Calculate expected transaction amount and fees
        arbitration_fee = Decimal(settings.ARBITRATION_FEE).quantize(Decimal('0.00000000'))/100000000
        trading_fee = Decimal(settings.TRADING_FEE).quantize(Decimal('0.00000000'))/100000000
        amount = contract.order.crypto_amount
        
        arbiter_exists = False
        servicer_exists = False
        buyer_exists = False
        seller_exists = False

        for out in tx_outputs:
            output_address = out.get('address')
            output_amount = Decimal(out.get('amount')).quantize(Decimal('0.00000000'))

            outputs.append({
                "address": output_address,
                "amount": str(output_amount)
            })
            
            # Checks if the current address is the arbiter
            # and set valid=False if fee is incorrect
            if output_address == arbiter:
                if output_amount != arbitration_fee:
                    error_msg = 'arbiter incorrect output_amount'
                    logger.error(error_msg)
                    valid = False
                    break
                arbiter_exists = True
            
            # Checks if the current address is the servicer 
            # and set valid=False if fee is incorrect
            if output_address == servicer:    
                if output_amount != trading_fee:
                    error_msg = 'servicer incorrect output_amount'
                    logger.error(error_msg)
                    valid = False
                    break
                servicer_exists = True

            if action == Transaction.ActionType.RELEASE:
                # If the action type is RELEASE, check if the current address is the buyer
                # and set valid=False if the amount is incorrect
                if output_address == buyer:
                    if output_amount != amount:
                        error_msg = 'buyer incorrect output_amount'
                        logger.warn(error_msg)
                        valid = False
                        break
                    buyer_exists = True
                
            if action == Transaction.ActionType.REFUND:
                # If the action type is REFUND, check if the current address is the seller
                # and set valid=False if the amount is incorrect
                if output_address == seller:
                    if output_amount != amount:
                        error_msg = 'seller incorrect output_amount'
                        logger.warn(error_msg)
                        valid = False
                        break
                    seller_exists = True
        
        '''
        Transaction is not valid if:
            (1) the arbiter or servicer is not found in the outputs, or
            (2) the transaction is for RELEASE but the buyer was not found, or
            (3) the transaction is for REFUND but the seller was not found
        '''
        if (not(arbiter_exists and servicer_exists) or
            ((action == Transaction.ActionType.RELEASE and not buyer_exists) or 
            (action == Transaction.ActionType.REFUND and not seller_exists))):
            valid = False

    # Initialize transaction details
    txdata = {
        "action": action,
        "txid": kwargs.get('txid'),
        "contract": contract.id
    }

    result = {
        "success": valid
    }

    status = None
    if valid:
        # Save transaction details 
        tx_serializer = TransactionSerializer(data=txdata)
        if tx_serializer.is_valid():
            tx_serializer = TransactionSerializer(tx_serializer.save())
        
        logger.warn(f"tx_serializer.data: {tx_serializer.data}")
        tx_id = tx_serializer.data.get("id")

        # Save transaction outputs
        for output in outputs:
            out_data = {
                "transaction": tx_id,
                "address": output.get('address'),
                "amount": output.get('amount')
            }
            recipient_serializer = RecipientSerializer(data=out_data)
            if recipient_serializer.is_valid():
                recipient_serializer = RecipientSerializer(recipient_serializer.save())
            else:
                logger.error(f'recipient_serializer.errors: {recipient_serializer.errors}')
        
        # Update order status
        status_type = None
        if action == Transaction.ActionType.REFUND:
            status_type = StatusType.REFUNDED
        if action == Transaction.ActionType.RELEASE:
            status_type = StatusType.RELEASED
        if action == Transaction.ActionType.ESCROW:
            status_type = StatusType.ESCROWED

        status = utils.update_order_status(contract.order.id, status_type).data

        txdata["outputs"] = outputs
        result["status"] = status
        result["txdata"] = txdata
    else:
        result["error"] = error_msg
    
    logger.warning(f'result: {result}')

    # Send the result through websocket
    return send_order_update(
        result, 
        contract.order.id
    )
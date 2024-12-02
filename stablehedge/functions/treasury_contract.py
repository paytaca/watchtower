import logging
from django.conf import settings
from django.db.models import Sum

from stablehedge.apps import LOGGER
from stablehedge import models
from stablehedge.js.runner import ScriptFunctions
from stablehedge.exceptions import StablehedgeException
from stablehedge.utils.wallet import to_cash_address, wif_to_cash_address, is_valid_wif
from stablehedge.utils.blockchain import broadcast_transaction
from stablehedge.utils.transaction import tx_model_to_cashscript
from stablehedge.utils.encryption import encrypt_str, decrypt_str


from main import models as main_models

def save_signature_to_tx(
    treasury_contract:models.TreasuryContract,
    tx_data:dict,
    sig:list,
    sig_index:int
):
    verify_result = ScriptFunctions.verifyTreasuryContractMultisigTx(dict(
        contractOpts=treasury_contract.contract_opts,
        sig=sig,
        locktime=tx_data.get("locktime", 0),
        inputs=tx_data["inputs"],
        outputs=tx_data["outputs"],
    ))

    if not verify_result.get("valid"):
        logging.exception(f"verify_result | {treasury_contract_address.address} | {verify_result}")
        raise StablehedgeException("Invalid signature/s", code="invalid_signature")

    sig_index = int(sig_index)
    if sig_index < 1 or sig_index > 3:
        raise StablehedgeException("Invalid index for signature", code="invalid_sig_index")
    tx_data[f"sig{sig_index}"] = sig

    return tx_data


def get_spendable_sats(treasury_contract_address:str):
    utxos = get_bch_utxos(treasury_contract_address)

    if isinstance(utxos, list):
        total_sats = 0
        for utxo in utxos:
            total_sats += utxo.value

        utxo_count = len(utxos)
    else:
        total_sats = utxos.aggregate(total_sats = Sum("value"))["total_sats"] or 0
        utxo_count = utxos.count()
 
    # estimate of sats used as fee when using the utxo
    # need to improve
    fee_sats_per_input = 500
    spendable_sats = total_sats - (fee_sats_per_input * utxo_count)

    return dict(total=total_sats, spendable=spendable_sats, utxo_count=utxo_count)


def find_single_bch_utxo(treasury_contract_address:str, satoshis:int):
    address = to_cash_address(treasury_contract_address, testnet=settings.BCH_NETWORK == "chipnet")
    return main_models.Transaction.objects.filter(
        address__address=address,
        token__name="bch",
        spent=False,
        value=satoshis,
    ).first()


def get_bch_utxos(treasury_contract_address:str, satoshis:int=None):
    address = to_cash_address(treasury_contract_address, testnet=settings.BCH_NETWORK == "chipnet")
    utxos = main_models.Transaction.objects.filter(
        address__address=address,
        token__name="bch",
        spent=False,
    )
    if satoshis is None:
        return utxos

    P2PKH_OUTPUT_FEE = 44
    fee_sats_per_input = 500

    subtotal = 0
    sendable = 0 - (P2PKH_OUTPUT_FEE * 2) # 2 outputs for send and change
    _utxos = []
    for utxo in utxos:
        subtotal += utxo.value
        sendable += utxo.value - fee_sats_per_input
        _utxos.append(utxo)

        if sendable >= satoshis:
            break


    return _utxos


def get_funding_wif_address(treasury_contract_address:str, token=False):
    funding_wif = get_funding_wif(treasury_contract_address)
    if not funding_wif:
        return

    testnet = treasury_contract_address.startswith("bchtest:")
    return wif_to_cash_address(funding_wif, testnet=testnet, token=token)

def set_funding_wif(treasury_contract_address:str, wif:str):
    treasury_contract = models.TreasuryContract.objects.get(address=treasury_contract_address)
    if not is_valid_wif(wif):
        raise Exception("Invalid WIF")

    cleaned_wif = wif
    if wif.startswith("bch-wif:"):
        cleaned_wif = wif
    else:
        cleaned_wif = encrypt_str(wif)

    # check if it convertible to address
    wif_to_cash_address(wif.replace("bch-wif:", ""))

    treasury_contract.encrypted_funding_wif = cleaned_wif
    treasury_contract.save()
    return treasury_contract

def get_funding_wif(treasury_contract_address:str):
    encrypted_funding_wif = models.TreasuryContract.objects \
        .filter(address=treasury_contract_address) \
        .values_list("encrypted_funding_wif", flat=True) \
        .first()
    
    if not encrypted_funding_wif: return 

    # in case the saved data is not encrypted
    if is_valid_wif(encrypted_funding_wif):
        return encrypted_funding_wif.replace("bch-wif:", "")

    funding_wif = decrypt_str(encrypted_funding_wif)

    return funding_wif


def sweep_funding_wif(treasury_contract_address:str):
    LOGGER.info(f"SWEEP FUNDING WIF | {treasury_contract_address}")
    funding_wif = get_funding_wif(treasury_contract_address)
    funding_wif_address = get_funding_wif_address(treasury_contract_address)

    utxos = main_models.Transaction.objects \
        .filter(spent=False, address__address=funding_wif_address)

    cashscript_utxos = []
    for utxo in utxos:
        cashscript_utxo = tx_model_to_cashscript(utxo)
        cashscript_utxo["wif"] = funding_wif
        cashscript_utxos.append(cashscript_utxo)

    if not len(cashscript_utxos):
        raise StablehedgeException("No UTXOs found in funding wif")

    tx_result = ScriptFunctions.sweepUtxos(dict(
        recipientAddress=treasury_contract_address,
        locktime=0,
        utxos=cashscript_utxos,
    ))

    if not tx_result["success"]:
        raise StablehedgeException(tx_result["error"])

    transaction = tx_result["transaction"]
    success, error_or_txid = broadcast_transaction(transaction)

    LOGGER.info(f"SWEEP FUNDING WIF | {treasury_contract_address} | {error_or_txid}")

    if not success:
        raise StablehedgeException(error_or_txid)

    return error_or_txid
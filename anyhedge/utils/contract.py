from ..js.runner import AnyhedgeFunctions

def create_contract(
    satoshis:int=0,
    low_price_multiplier:float=0.9,
    high_price_multiplier:float=2,
    duration_seconds:int=0,
    hedge_address:str="",
    hedge_pubkey:str="",
    short_address:str="",
    short_pubkey:str="",
):
    intent =  {
        "amount": satoshis/10**8,
        "lowPriceMult": low_price_multiplier,
        "highPriceMult": high_price_multiplier,
        "duration": duration_seconds,
    }
    pubkeys = {
        "hedgeAddress": hedge_address,
        "hedgePubkey": hedge_pubkey,
        "shortAddress": short_address,
        "shortPubkey": short_pubkey,
    }
    return AnyhedgeFunctions.create(intent, pubkeys)

def compile_contract(
    nominal_units:int=0,
    duration:int=0,
    startPrice:int=0,
    startTimestamp:int=0,
    oraclePublicKey:str="",
    highLiquidationPriceMultiplier:float=0.0,
    lowLiquidationPriceMultiplier:float=0.0,
    hedgePublicKey:str="",
    longPublicKey:str="",
    hedgeAddress:str="",
    longAddress:str="",
):
    data = {
        "nominalUnits": nominal_units,
        "duration": duration,
        "startPrice": startPrice,
        "startTimestamp": startTimestamp,
        "oraclePublicKey": oraclePublicKey,
        "highLiquidationPriceMultiplier": highLiquidationPriceMultiplier,
        "lowLiquidationPriceMultiplier": lowLiquidationPriceMultiplier,
        "hedgePublicKey": hedgePublicKey,
        "longPublicKey": longPublicKey,
        "hedgeAddress": hedgeAddress,
        "longAddress": longAddress,
    }

    return AnyhedgeFunctions.compileContract(data)
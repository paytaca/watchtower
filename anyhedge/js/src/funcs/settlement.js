import { AnyHedgeManager } from '@generalprotocols/anyhedge'
// import { AnyHedgeManager as AnyHedgeManagerOld } from '@generalprotocols/anyhedge-old'
import { parseOracleMessage, getPriceMessages } from "./price.js"

/**
 * 
 * @param {String[]} rawTxs 
 */
export async function parseSettlementTransactions(rawTxs) {
  const response = { success: false, settlements: [], error: undefined }

  if (!Array.isArray(rawTxs)) {
    response.success = false
    response.error = 'expected array of raw transactions'
  }

  // const managerOld = new AnyHedgeManagerOld()
  const manager = new AnyHedgeManager()
  const txPromises = rawTxs.map(manager.parseSettlementTransaction)
  response.settlements = await Promise.allSettled(txPromises)
  response.settlements = response.settlements.map(result => result?.value)
  response.success = true
  // response.settlements = await Promise.allSettled(rawTxs.map(async (rawTx) => {
  //   try {
  //     settlement = manager.parseSettlementTransaction(rawTx)
  //     if (!settlement) throw new Error('No settlement')
  //   } catch {
  //     settlement = managerOld.parseSettlementTransaction(rawTx)
  //   }
  //   return settlement
  // }))
  return response
}

/**
 * 
 * @param {Object} contractData 
 * @param {PriceMessageConfig|undefined} oracleInfo
 */
export async function settleContractMaturity(contractData, oracleInfo) {
  const response = {
    success: false,
    settlementData: {},
    error: '',
  }
  const maturityTimestamp = contractData?.parameters?.maturityTimestamp
  const oraclePubKey = contractData?.metadata?.oraclePublicKey

  const priceMessageConfig = Object.assign({}, oracleInfo, { oraclePubKey: oraclePubKey })

  const getPriceMessagesResponse = await getPriceMessages(
    priceMessageConfig,

    // provided 60 second window, which is the rate of new price messages
    { maxMessageTimestamp: maturityTimestamp + 60, count: 5 }
  )

  let prevPrice, settlementPrice
  for (var i = 0; i <= getPriceMessagesResponse.results.length-2; i++) {
    const _prevPrice = getPriceMessagesResponse.results[i+1]
    const _settlementPrice = getPriceMessagesResponse.results[i]

    const _prevTimestamp = _prevPrice.priceData.messageTimestamp
    const _settlementTimestamp = _settlementPrice.priceData.messageTimestamp

    if (_prevTimestamp < maturityTimestamp && _settlementTimestamp >= maturityTimestamp) {
      prevPrice = _prevPrice
      settlementPrice = _settlementPrice
    }
  }

  if (!prevPrice || !settlementPrice) {
    response.success = false
    response.error = 'unable to find settlement price'
    return response
  }

  const contractSettlementParameters = {
    oraclePublicKey: oraclePubKey,
    settlementMessage: settlementPrice.priceMessage.message,
    settlementSignature: settlementPrice.priceMessage.signature,
    previousMessage: prevPrice.priceMessage.message,
    previousSignature: prevPrice.priceMessage.signature,
    contractFunding: contractData.fundings?.[0],
    contractMetadata: contractData.metadata,
    contractParameters: contractData.parameters,
  }

  const manager = new AnyHedgeManager()
  try {
    const settlementData = await manager.matureContractFunding(contractSettlementParameters)
    response.settlementData = settlementData
    response.success = true
  } catch(error) {
    response.error = 'Encoutered error in creating maturity payout'
    if (error?.message) response.error = error?.message
    response.success = false
  }
  return response
}

/**
 * 
 * @param {Object} contractData 
 * @param {OraclePriceMessage} prevPriceMessage
 * @param {OraclePriceMessage} settlementPriceMessage 
 */
export async function liquidateContract(contractData, prevPriceMessage, settlementPriceMessage) {
  const response = {
    success: false,
    settlementData: {},
    error: '',
  }

  const oraclePubKey = contractData?.metadata?.oraclePublicKey
  const parsePrevOracleMessageResponse = await parseOracleMessage(
    prevPriceMessage.message, oraclePubKey, prevPriceMessage.signature)
  if (!parsePrevOracleMessageResponse.success) {
    response.success = false
    response.error = parsePrevOracleMessageResponse.error || 'Invalid previous price message'
  }
  const parseSettlementOracleMessageResponse = await parseOracleMessage(
    settlementPriceMessage.message, oraclePubKey, settlementPriceMessage.signature)
  if (!parseSettlementOracleMessageResponse.success) {
    response.success = false
    response.error = parseSettlementOracleMessageResponse.error || 'Invalid settlement price message'
  }

  const contractSettlementParameters = {
    oraclePublicKey: oraclePubKey,
    settlementMessage: settlementPriceMessage.message,
    settlementSignature: settlementPriceMessage.signature,
    previousMessage: prevPriceMessage.message,
    previousSignature: prevPriceMessage.signature,
    contractFunding: contractData.funding?.[0],
    contractMetadata: contractData.metadata,
    contractParameters: contractData.parameters,
  }

  const manager = new AnyHedgeManager()
  try {
    const settlementData = await manager.liquidateContractFunding(contractSettlementParameters)
    response.settlementData = settlementData
    response.success = true
  } catch(error) {
    response.error = 'Encoutered error in creating liquidation payout'
    if (error?.message) response.error = error
    response.success = false
  }
  return response
}

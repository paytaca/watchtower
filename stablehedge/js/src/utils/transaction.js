import { SignatureTemplate } from "cashscript"
import { placeholder, scriptToBytecode } from "@cashscript/utils"
import { cashScriptOutputToLibauthOutput, createInputScript, getInputSize, getPreimageSize } from "cashscript/dist/utils.js";
import { cashAddressToLockingBytecode, hexToBin } from "@bitauth/libauth";

/**
 * Taken directly from Transaction class' fee calculation
 * Returns the bytesize of contract's transaction input
 * @param {Transaction} transaction
 */
export function calculateInputSize(transaction) {
  const placeholderArgs = transaction.args.map((arg) => (arg instanceof SignatureTemplate ? placeholder(71) : arg));
  // Create a placeholder preimage of the correct size
  const placeholderPreimage = transaction.abiFunction.covenant
      ? placeholder(getPreimageSize(scriptToBytecode(transaction.contract.redeemScript)))
      : undefined;
  // Create a placeholder input script for size calculation using the placeholder
  // arguments and correctly sized placeholder preimage
  const placeholderScript = createInputScript(transaction.contract.redeemScript, placeholderArgs, transaction.selector, placeholderPreimage);
  // Add one extra byte per input to over-estimate tx-in count
  const contractInputSize = getInputSize(placeholderScript) + 1;
  return contractInputSize
}


/**
 * @param {String} contractAddress
 * @param {Object} tx 
 * @param {Number} [tx.version]
 * @param {Number} tx.locktime
 * @param {import("cashscript").UtxoP2PKH[]} tx.inputs
 * @param {import("cashscript").Output[]} tx.outputs
 */
export function cashscriptTxToLibauth(contractAddress, tx) {
  const transaction = {
    version: tx?.version || 2,
    locktime: tx?.locktime,
    inputs: tx?.inputs?.map(input => {
      return {  
        outpointIndex: input?.vout,
        outpointTransactionHash: hexToBin(input?.txid),
        sequenceNumber: 0xfffffffe,
        unlockingBytecode: new Uint8Array(),
      }
    }),
    outputs: tx?.outputs?.map(cashScriptOutputToLibauthOutput),
  }

  const contractBytecode = cashAddressToLockingBytecode(contractAddress).bytecode
  const sourceOutputs = tx?.inputs?.map(input => {
    const sourceOutput = {
      to: input?.template?.unlockP2PKH()?.generateLockingBytecode?.() || contractBytecode,
      amount: BigInt(input?.satoshis),
      token: !input?.token ? undefined : {
        category: hexToBin(input?.token?.category),
        amount: BigInt(input?.token?.amount),
        nft: !input?.token?.nft ? undefined : {
          commitment: hexToBin(input?.token?.nft?.commitment),
          capability: input?.token?.nft?.capability,
        }
      },
    }

    return cashScriptOutputToLibauthOutput(sourceOutput);
  })

  return { transaction, sourceOutputs }
}
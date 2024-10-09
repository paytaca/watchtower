import { isHex } from '@bitauth/libauth'
import { TreasuryContract } from '../contracts/treasury-contract/index.js'
import { parseCashscriptOutput, parseUtxo } from '../utils/crypto.js'
import { SignatureTemplate } from 'cashscript'


export function getTreasuryContractArtifact() {
  const artifact = TreasuryContract.getArtifact();
  return { success: true, artifact }
}

/**
 * @param {Object} opts 
 */
export function compileTreasuryContract(opts) {
  const treasuryContract = new TreasuryContract(opts)
  const contract = treasuryContract.getContract()
  return {
    address: contract.address,
    tokenAddress: contract.tokenAddress,
    params: treasuryContract.params,
    options: treasuryContract.options,
    bytecode: contract.bytecode,
  }
}

/**
 * @param {Object} opts 
 * @param {Object} opts.contractOpts 
 * @param {import('cashscript').UtxoP2PKH} opts.authKeyUtxo 
 * @param {import('cashscript').UtxoP2PKH[]} opts.contractUtxos
 * @param {import('cashscript').UtxoP2PKH} opts.recipientAddress
 * @param {import('cashscript').UtxoP2PKH} opts.authKeyRecipient
 * @param {Number} [opts.locktime]
 */
export async function sweepTreasuryContract(opts) {
  const treasuryContract = new TreasuryContract(opts?.contractOpts)
  const authKeyUtxo = parseUtxo(opts?.authKeyUtxo)
  let contractUtxos = undefined
  if (opts?.contractUtxos?.length) contractUtxos = opts.contractUtxos.map(parseUtxo)
  const transaction = await treasuryContract.sweep({
    contractUtxos,
    authKeyUtxo, 
    recipientAddress: opts?.recipientAddress,
    authKeyRecipient: opts?.authKeyRecipient,
  })
  if (typeof transaction === 'string') return { success: false, error: transaction }
  return { success: true, tx_hex: await transaction.build() }
}

/**
 * @param {Object} opts
 * @param {Object} opts.contractOpts
 * @param {import('cashscript').Utxo[]} opts.inputs
 * @param {import('cashscript').Output} opts.outputs
 * @param {String} opts.sig1
 * @param {String} opts.sig1
 * @param {String} opts.sig1
 * @param {Number} [opts.locktime]
 */
export async function unlockTreasuryContractWithMultiSig(opts) {
  const treasuryContract = new TreasuryContract(opts?.contractOpts)

  const inputs = opts?.inputs?.map(parseUtxo)
  const outputs = opts?.outputs?.map(parseCashscriptOutput)

  const transaction = await treasuryContract.unlockWithMultiSig({
    inputs, outputs,
    sig1: isHex(opts?.sig1) ? opts?.sig1 : new SignatureTemplate(opts?.sig1),
    sig2: isHex(opts?.sig2) ? opts?.sig2 : new SignatureTemplate(opts?.sig2),
    sig3: isHex(opts?.sig3) ? opts?.sig3 : new SignatureTemplate(opts?.sig3),
    locktime: opts?.locktime,
  })

  if (typeof transaction === 'string') return { success: false, error: transaction }
  return { success: true, tx_hex: await transaction.build() }
}


/**
 * @param {Object} opts
 * @param {Object} opts.contractOpts
 * @param {Boolean} [opts.keepGuarded]
 * @param {import('cashscript').Utxo[]} opts.inputs
 * @param {import('cashscript').Output} opts.outputs
 * @param {Number} [opts.locktime]
 */
export async function unlockTreasuryContractWithNft(opts) {
  const treasuryContract = new TreasuryContract(opts?.contractOpts)

  const inputs = opts?.inputs?.map(parseUtxo)
  const outputs = opts?.outputs?.map(parseCashscriptOutput)

  const transaction = await treasuryContract.unlockWithNft({
    keepGuarded: opts?.keepGuarded,
    inputs, outputs,
    locktime: opts?.locktime,
  })

  if (typeof transaction === 'string') return { success: false, error: transaction }
  return { success: true, tx_hex: await transaction.build() }
}

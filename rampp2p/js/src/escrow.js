const { ElectrumNetworkProvider, Contract } = require('cashscript');
const { compileFile } = require('cashc');
const path = require('path');
const BCHJS = require('@psf/bch-js');
const CryptoJS = require('crypto-js');

const ARBITER_PUBKEY = process.argv[2]
const BUYER_PUBKEY = process.argv[3]
const SELLER_PUBKEY = process.argv[4]
const TIMESTAMP = process.argv[5]
const SERVICER_PUBKEY = process.env.SERVICER_PK
const SERVICE_FEE = parseInt(process.env.SERVICE_FEE)
const ARBITRATION_FEE = parseInt(process.env.ARBITRATION_FEE)

const bchjs = new BCHJS({
    restURL: 'https://bchn.fullstack.cash/v5/',
    apiToken: process.env.BCHJS_TOKEN
  });

const NETWORK = process.env.ESCROW_NETWORK;

(async () => {

    // Compile the escrow contract to an artifact object
    const artifact = compileFile(path.join(__dirname, 'escrow.cash'));
    // Initialise a network provider for network operations
    let provider = new ElectrumNetworkProvider();
    if (NETWORK === 'chipnet') provider = new ElectrumNetworkProvider(NETWORK)
    const [arbiterPkh, buyerPkh, sellerPkh, servicerPkh] = getPubKeyHash();
    
    // Generate contract hash with timestamp
    const contractHash = await calculateSHA256(arbiterPkh, buyerPkh, sellerPkh, servicerPkh, TIMESTAMP)

    // Instantiate a new contract providing the constructor parameters
    const contractParams = [arbiterPkh, buyerPkh, sellerPkh, servicerPkh, SERVICE_FEE, ARBITRATION_FEE, contractHash];
    const contract = new Contract(artifact, contractParams, provider);

    data = `{"success": "true", "contract_address" : "${contract.address}"}`
    console.log(data)
})();

function getPubKeyHash() {  
    // produce the public key hashes
    const arbiterPkh = bchjs.Crypto.hash160(Buffer.from(ARBITER_PUBKEY, "hex"));
    const buyerPkh = bchjs.Crypto.hash160(Buffer.from(BUYER_PUBKEY, "hex"));
    const sellerPkh = bchjs.Crypto.hash160(Buffer.from(SELLER_PUBKEY, "hex"));
    const servicerPkh = bchjs.Crypto.hash160(Buffer.from(SERVICER_PUBKEY, "hex"));
    return [arbiterPkh, buyerPkh, sellerPkh, servicerPkh];
}

async function calculateSHA256(arbiterPkh, buyerPkh, sellerPkh, servicerPkh, timestamp) {
    const message = arbiterPkh + buyerPkh + sellerPkh + servicerPkh + timestamp
    const hash = CryptoJS.SHA256(message);
    const contractHash = hash.toString()
    return contractHash
}
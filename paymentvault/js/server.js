import express from 'express'
import { getContract } from './funcs'


const port = 3002
const app = express()


app.get('/payment-vaults/:userPubkey/:merchantPubkey/', async (req, res) => {
  const opts = {
    options: {
      network: req.query.network
    },
    ...req.params,
  }
  const result = await getContract(opts)
  res.send(result)
})


app.listen(port, () => console.log(`Server listening on port ${port}`))
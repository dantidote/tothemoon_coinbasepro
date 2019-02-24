#!/usr/bin/python

import gdax
import json
import logging
import configparser
from datetime import datetime, timedelta, date

config = configparser.ConfigParser(inline_comment_prefixes='#')
config.read('gdax.config')

bank_acct_id = config['DEFAULT']['bank_acct_id']
buy_amount_btcusd = float(config['DEFAULT']['buy_amount_btcusd'])
buy_amount_ethusd = float(config['DEFAULT']['buy_amount_ethusd'])
fund_usd_threshold = float(config['DEFAULT']['fund_usd_threshold'])
fund_usd_amount = float(config['DEFAULT']['fund_usd_amount'])
btc_withdrawal_threshold = float(config['DEFAULT']['btc_withdrawal_threshold'])
btc_withdrawal_address = config['DEFAULT']['btc_withdrawal_address']
recent_deposit_max = float(config['DEFAULT']['recent_deposit_max'])

logging.basicConfig(filename=config['DEFAULT']['logfile'],level=logging.DEBUG)

client = gdax.AuthenticatedClient(config['DEFAULT']['key'], config['DEFAULT']['secret'], config['DEFAULT']['passphrase'])

accounts = client.get_accounts()

logging.debug( json.dumps(accounts, indent=4) )

#Loop through accounts to get an account for each currency
for account in accounts:
  if account["currency"] == 'USD' :
    usd_account = account
  elif account["currency"] == 'BTC' :
    btc_account = account
  elif account["currency"] == 'ETH' :
    eth_account = account

transfers = client.get_account_transfers(usd_account["id"])

logging.debug( json.dumps(transfers, indent=4) )

#Loop through transfers from the USD account, and sum the pending deposits.
all_deposits = 0
recent_deposit_sum = 0
for transfer in transfers:
  if transfer["details"].get("coinbase_payment_method_type") == "ach_bank_account" and transfer["type"] == "deposit" and datetime.strptime( transfer["created_at"], "%Y-%m-%d %H:%M:%S.%f+00" ) > datetime.utcnow() - timedelta(days=30) :
    recent_deposit_sum += float(transfer["amount"])

  if transfer["type"] == "deposit" and transfer["completed_at"] is None:
    all_deposits += float(transfer["amount"])


#deposit
if recent_deposit_sum >= recent_deposit_max:
  logging.debug("Last 30 days: $%d \t Limit: $%d" % (recent_deposit_sum, recent_deposit_max) )
  logging.info("You've depoisted more than your monthly limit.  Not depositing more.")

elif float(usd_account["available"]) + all_deposits < fund_usd_threshold :
  logging.info("Current balance of $%d and Pending Transfers of $%d is less than $%d.  Adding more funds +$%d " % (float(usd_account["available"]), all_deposits, fund_usd_threshold, fund_usd_amount) )
  ret = client.deposit( fund_usd_amount, "USD", bank_acct_id )
  logging.debug( json.dumps(ret, indent=4) )
else:
  logging.info("Not depositing more funds." )  


#withdraw
if float(btc_account["available"]) > btc_withdrawal_threshold:
  logging.info("BTC balance is greater than %sBTC. Withdrawing all (%s)" % (btc_withdrawal_threshold, btc_account["available"]) )
  client.crypto_withdraw(btc_account["available"], "BTC", btc_withdrawal_address)

#current price BTC
curprice = float(client.get_product_ticker("BTC-USD")["bid"])
buy_price_btc = curprice
logging.debug("buy_price_btc: %s" % buy_price_btc)
buy_size_btc = "%.8f" % max(buy_amount_btcusd / buy_price_btc, 0.001)
logging.debug("buy_size_btc: %s" % buy_size_btc)

#current price ETH
curprice = float(client.get_product_ticker("ETH-USD")["bid"])
buy_price_eth = curprice
logging.debug("buy_price_eth: %s" % buy_price_eth)
buy_size_eth = "%.6f" % max(buy_amount_ethusd / buy_price_eth, 0.01)
logging.debug("buy_size: %s" % buy_size_eth)

#buy
if float(usd_account["available"]) >= buy_amount_btcusd + buy_amount_ethusd :
  logging.info("Buying $%d of BTC" % buy_amount_btcusd)
  ret = client.buy(type="limit", price=buy_price_btc, size=buy_size_btc, post_only=True,  product_id= "BTC-USD")
#logging.debug( json.dumps(ret, indent=4) )

  logging.info("Buying $%d of ETH" % buy_amount_ethusd)
  ret = client.buy(type="limit", price=buy_price_eth, size=buy_size_eth, post_only=True,  product_id= "ETH-USD")
#  logging.debug( json.dumps(ret, indent=4) )

else :
  logging.info("Not enough USD to buy BTC")


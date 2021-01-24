#!/bin/bash

# Debug flag
#debug='-v'
keystore_file=../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c

debug=''
abi_dir=${ETH_ABI_DIR:-/usr/local/share/cic/solidity/abi}

# Determine token amount
token_amount=${DEV_ETH_RESERVE_AMOUNT:0:-1}

# Determine gas amount
#gas_amount=20000000000000000000
gas_amount=2000000000000000000

export DATABASE_NAME=$DATABASE_NAME_CIC_ETH
export DATABASE_PORT=$HTTP_PORT_POSTGRES
export DATABASE_HOST=localhost

set -e
set -a

old_gas_provider=$DEV_ETH_ACCOUNT_GAS_PROVIDER
DEV_ETH_ACCOUNT_GAS_GIFTER=`python ./create.py --no-register`
echo DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_GAS_GIFTER
export DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_GAS_GIFTER
cic-eth-tag GAS_GIFTER $DEV_ETH_ACCOUNT_GAS_GIFTER

DEV_ETH_ACCOUNT_SARAFU_GIFTER=`python ./create.py --no-register`
echo DEV_ETH_ACCOUNT_SARAFU_GIFTER=$DEV_ETH_ACCOUNT_SARAFU_GIFTER
export DEV_ETH_ACCOUNT_SARAFU_GIFTER=$DEV_ETH_ACCOUNT_SARAFU_GIFTER
cic-eth-tag SARAFU_GIFTER $DEV_ETH_ACCOUNT_SARAFU_GIFTER


DEV_ETH_ACCOUNT_APPROVAL_ESCROW_OWNER=`python ./create.py --no-register`
echo DEV_ETH_ACCOUNT_APPROVAL_ESCROW_OWNER=$DEV_ETH_ACCOUNT_APPROVAL_ESCROW_OWNER
export DEV_ETH_ACCOUNT_APPROVAL_ESCROW_OWNER=$DEV_ETH_ACCOUNT_APPROVAL_ESCROW_OWNER
cic-eth-tag TRANSFER_APPROVAL_OWNER $DEV_ETH_ACCOUNT_APPROVAL_ESCROW_OWNER


DEV_ETH_ACCOUNT_SINGLE_SHOT_FAUCET_OWNER=`python ./create.py --no-register`
echo DEV_ETH_ACCOUNT_SINGLE_SHOT_FAUCET_OWNER=$DEV_ETH_ACCOUNT_SINGLE_SHOT_FAUCET_OWNER
export DEV_ETH_ACCOUNT_SINGLE_SHOT_FAUCET_OWNER=$DEV_ETH_ACCOUNT_SINGLE_SHOT_FAUCET_OWNER
cic-eth-tag FAUCET_OWNER $DEV_ETH_ACCOUNT_SINGLE_SHOT_FAUCET_OWNER


DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=`python ./create.py --no-register`
echo DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=$DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER
export DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=$DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER
cic-eth-tag ACCOUNTS_INDEX_WRITER $DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER


# Transfer gas to custodial gas provider adddress
#echo $old_gas_provider
>&2 echo gift gas to gas gifter
>&2 echo "python gas.py -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_GAS_GIFTER $gas_amount"
>&2 python gas.py -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_GAS_GIFTER $gas_amount

>&2 echo gift gas to sarafu token owner
>&2 echo "python gas.py -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_SARAFU_OWNER $gas_amount"
>&2 python gas.py -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_SARAFU_OWNER $gas_amount

>&2 echo gift gas to account index owner
>&2 echo "python gas.py -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_OWNER $gas_amount"
>&2 python gas.py -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_OWNER $gas_amount


# Send reserve to token creator
>&2 giftable-token-gift -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_ETH_RESERVE_ADDRESS --recipient $DEV_ETH_ACCOUNT_SARAFU_OWNER -w $debug $token_amount


# Create token
#DEV_ETH_SARAFU_TOKEN_ADDRESS=`cic-bancor-token -p $ETH_PROVIDER -r $CIC_REGISTRY_ADDRESS -z $DEV_ETH_RESERVE_ADDRESS -o $DEV_ETH_ACCOUNT_SARAFU_OWNER -n $DEV_ETH_SARAFU_TOKEN_NAME -s $DEV_ETH_SARAFU_TOKEN_SYMBOL -d $DEV_ETH_SARAFU_TOKEN_DECIMALS -i $CIC_CHAIN_SPEC $debug $token_amount`
DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_RESERVE_ADDRESS
echo DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_SARAFU_TOKEN_ADDRESS 
export DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_SARAFU_TOKEN_ADDRESS 


# Transfer tokens to gifter address
>&2 python transfer.py -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --token-address $DEV_ETH_SARAFU_TOKEN_ADDRESS --abi-dir $abi_dir -w $debug $DEV_ETH_ACCOUNT_SARAFU_GIFTER ${token_amount:0:-1}

# Deploy transfer approval contract
CIC_APPROVAL_ESCROW_ADDRESS=`erc20-approval-escrow-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --approver $DEV_ETH_ACCOUNT_APPROVAL_ESCROW_OWNER -w $debug`
echo CIC_APPROVAL_ESCROW_ADDRESS=$CIC_APPROVAL_ESCROW_ADDRESS 
export CIC_APPROVAL_ESCROW_ADDRESS=$CIC_APPROVAL_ESCROW_ADDRESS 

# Register transfer approval contract
>&2 cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -k TransferApproval -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $CIC_APPROVAL_ESCROW_ADDRESS

# Deploy one-time token faucet for newly created token
DEV_ETH_SARAFU_FAUCET_ADDRESS=`erc20-single-shot-faucet-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --token-address $DEV_ETH_SARAFU_TOKEN_ADDRESS --editor $DEV_ETH_ACCOUNT_SINGLE_SHOT_FAUCET_OWNER --set-amount 1048576 -w $debug`
echo DEV_ETH_SARAFU_FAUCET_ADDRESS=$DEV_ETH_SARAFU_FAUCET_ADDRESS 
export DEV_ETH_SARAFU_FAUCET_ADDRESS=$DEV_ETH_SARAFU_FAUCET_ADDRESS 

# Transfer tokens to faucet contract
>&2 python transfer.py  -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --token-address $DEV_ETH_SARAFU_TOKEN_ADDRESS --abi-dir $abi_dir -w $debug $DEV_ETH_SARAFU_FAUCET_ADDRESS ${token_amount:0:-1}

# Registry faucet entry
>&2 cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -k Faucet -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_SARAFU_FAUCET_ADDRESS

# Deploy token endorser registry
#DEV_ETH_TOKEN_ENDORSER_ADDRESS=`eth-token-endorser-deploy -p $ETH_PROVIDER -o $DEV_ETH_ACCOUNT_SARAFU_OWNER $debug`
#echo DEV_ETH_TOKEN_ENDORSER_ADDRESS=$DEV_ETH_TOKEN_ENDORSER_ADDRESS
#export DEV_ETH_TOKEN_ENDORSER_ADDRESS=$DEV_ETH_TOKEN_ENDORSER_ADDRESS
#ENDORSEMENT_MSG=`echo -n 'very cool token' | sha256sum | awk '{print $1;}'`
#>&2 eth-token-endorser-add -p $ETH_PROVIDER -a $DEV_ETH_TOKEN_ENDORSER_ADDRESS -t $DEV_ETH_SARAFU_TOKEN_ADDRESS -o $DEV_ETH_ACCOUNT_SARAFU_OWNER $debug $ENDORSEMENT_MSG
CIC_TOKEN_INDEX_ADDRESS=`eth-token-index-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug`
echo CIC_TOKEN_INDEX_ADDRESS=$CIC_TOKEN_INDEX_ADDRESS
export CIC_TOKEN_INDEX_ADDRESS=$CIC_TOKEN_INDEX_ADDRESS
>&2 eth-token-index-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_TOKEN_INDEX_ADDRESS -w $debug $DEV_ETH_SARAFU_TOKEN_ADDRESS

# Register token registry
>&2 cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -k TokenRegistry -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER $CIC_TOKEN_INDEX_ADDRESS

# Deploy address declarator registry
declarator_description=0x546869732069732074686520434943206e6574776f726b000000000000000000
CIC_DECLARATOR_ADDRESS=`eth-address-declarator-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $declarator_description`
echo CIC_DECLARATOR_ADDRESS=$CIC_DECLARATOR_ADDRESS
export CIC_DECLARATOR_ADDRESS=$CIC_DECLARATOR_ADDRESS
token_description_one=`sha256sum sarafu_declaration.json | awk '{ print $1; }'`
token_description_two=0x54686973206973207468652053617261667520746f6b656e0000000000000000
>&2 eth-address-declarator-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_DECLARATOR_ADDRESS -w $debug $DEV_ETH_SARAFU_TOKEN_ADDRESS $token_description_one
>&2 eth-address-declarator-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_DECLARATOR_ADDRESS -w $debug $DEV_ETH_SARAFU_TOKEN_ADDRESS $token_description_two


# Register address declarator
>&2 cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -k AddressDeclarator -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER $CIC_DECLARATOR_ADDRESS 

# We're done with the registry at this point, seal it off
>&2 cic-registry-seal -y $keystore_file -i $CIC_CHAIN_SPEC -r $CIC_REGISTRY_ADDRESS -p $ETH_PROVIDER


# Add accounts index writer with key from keystore
>&2 eth-accounts-index-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_ACCOUNTS_INDEX_ADDRESS --writer $DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER -w $debug

set +a
set +e

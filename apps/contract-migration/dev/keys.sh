#!/bin/bash

mkdir -vp .tmp
echo -n '' > .tmp/.env_accounts
account_labels=(
	DEV_ETH_ACCOUNT_BANCOR_DEPLOYER
	DEV_ETH_ACCOUNT_GAS_PROVIDER
	DEV_ETH_ACCOUNT_RESERVE_OWNER
	DEV_ETH_ACCOUNT_RESERVE_MINTER
	DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_OWNER
	DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER
	DEV_ETH_ACCOUNT_SARAFU_OWNER
	DEV_ETH_ACCOUNT_SARAFU_GIFTER
	DEV_ETH_ACCOUNT_APPROVAL_ESCROW_OWNER
	DEV_ETH_ACCOUNT_SINGLE_SHOT_FAUCET_OWNER
)
bip39gen -n ${#account_labels[@]} "$DEV_MNEMONIC"
i=0
for a in `bip39gen -n ${#account_labels[@]} "$DEV_MNEMONIC" | jq -r .address[]`; do
	exportline=${account_labels[$i]}=$a
	export $exportline
	echo $exportline >> .tmp/.env_accounts
	echo exportline $exportline
	i=$(($i+1))
done


import { JSONSerializable } from './format';

const ENGINE_NAME = 'automerge';
const ENGINE_VERSION = '0.14.1';

const NETWORK_NAME = 'cic';
const NETWORK_VERSION = '1';

const CRYPTO_NAME = 'pgp';
const CRYPTO_VERSION = '2';

type VersionedSpec = {
	name:		string
	version: 	string
	ext?:		Object
}

const engineSpec:VersionedSpec = {
	name: ENGINE_NAME,
	version: ENGINE_VERSION,			
}

const cryptoSpec:VersionedSpec = {
	name: CRYPTO_NAME,
	version: CRYPTO_VERSION,
}

const networkSpec:VersionedSpec = {
	name: NETWORK_NAME,
	version: NETWORK_VERSION,
}

export {
	engineSpec,
	cryptoSpec,
	networkSpec,
	VersionedSpec,
};

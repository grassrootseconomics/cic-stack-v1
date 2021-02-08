import * as crypto from 'crypto';

const _algs = {
	'SHA-256': 'sha256',
}

function cryptoWrapper() {
}

cryptoWrapper.prototype.digest = async function(s, d) {
	const h = crypto.createHash(_algs[s]);
	h.update(d);
	return h.digest();
}

let subtle = undefined;
if (typeof window !== 'undefined') {
	subtle = window.crypto.subtle;
} else {
	subtle = new cryptoWrapper();
}


export {
	subtle,
}


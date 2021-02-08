import * as pgp from 'openpgp';
import * as crypto from 'crypto';

interface Signable {
	digest():string;
}

type KeyGetter = () => any;

type Signature = {
	engine:string
	algo:string
	data:string
	digest:string
}

interface Signer { 
	prepare(Signable):boolean;
	onsign(Signature):void;
	onverify(boolean):void;
	sign(digest:string):void
	verify(digest:string, signature:Signature):void
	fingerprint():string
}

interface Authoritative {
}

interface KeyStore {
	getPrivateKey:		KeyGetter
	getFingerprint:		() => string
	getTrustedKeys: 	() => Array<any>
	getTrustedActiveKeys: 	() => Array<any>
	getEncryptKeys: 	() => Array<any>
}

class PGPKeyStore implements KeyStore {

	fingerprint:	string
	pk:		any

	pubk = {
		active: [],
		trusted: [],
		encrypt: [],
	}
	loads = 0x00;
	loadsTarget = 0x0f;
	onload: (k:KeyStore) => void;

	constructor(passphrase:string, pkArmor:string, pubkActiveArmor:string, pubkTrustedArmor:string, pubkEncryptArmor:string, onload = (ks:KeyStore) => {}) {
		this._readKey(pkArmor, undefined, 1, passphrase);
		this._readKey(pubkActiveArmor, 'active', 2);
		this._readKey(pubkTrustedArmor, 'trusted', 4);
		this._readKey(pubkEncryptArmor, 'encrypt', 8);
		this.onload = onload;
	}

	private _readKey(a:string, x:any, n:number, pass?:string) {
		pgp.key.readArmored(a).then((k) => {
			if (pass !== undefined) {
				this.pk = k.keys[0];
				this.pk.decrypt(pass).then(() => {
					this.fingerprint = this.pk.getFingerprint();
					console.log('private key (sign)', this.fingerprint);
					this._registerLoad(n);
				});
			} else {
				this.pubk[x] = k.keys;
				k.keys.forEach((pubk) => {
					console.log('public key (' + x + ')', pubk.getFingerprint());
				});
				this._registerLoad(n);
			}
		});
	}

	private _registerLoad(b:number) {
		this.loads |= b;
		if (this.loads == this.loadsTarget) {
			this.onload(this);
		}
	}

	public getTrustedKeys(): Array<any> {
		return this.pubk['trusted'];
	}

	public getTrustedActiveKeys(): Array<any> {
		return this.pubk['active'];

	}

	public getEncryptKeys(): Array<any> {
		return this.pubk['encrypt'];

	}

	public getPrivateKey(): any {
		return this.pk;
	}

	public getFingerprint(): string {
		return this.fingerprint;
	}
}

class PGPSigner implements Signer {

	engine	= 'pgp'
	algo	= 'sha256'
	dgst:		string
	signature:	Signature
	keyStore:	KeyStore
	onsign:		(Signature) => void
	onverify:	(boolean) => void

	constructor(keyStore:KeyStore) {
		this.keyStore = keyStore
		this.onsign = (string) => {};
		this.onverify = (boolean) => {};
	}

	public fingerprint(): string {
		return this.keyStore.getFingerprint();
	}

	public prepare(material:Signable):boolean {
		this.dgst = material.digest();
		return true;
	}

	public verify(digest:string, signature:Signature) {
		pgp.signature.readArmored(signature.data).then((s) => {
			const opts = {
				message: pgp.cleartext.fromText(digest),
				publicKeys: this.keyStore.getTrustedKeys(),
				signature: s,
			};
			pgp.verify(opts).then((v) => {
				let i = 0;
				for (i = 0; i < v.signatures.length; i++) {
					const s = v.signatures[i];
					if (s.valid) {
						this.onverify(s);
						return;
					}
				}
				console.error('checked ' + i + ' signature(s) but none valid');
				this.onverify(false);
			});
		}).catch((e) => {
			console.error(e);
			this.onverify(false);
		});
	}

	public sign(digest:string) {
		const m = pgp.cleartext.fromText(digest);
		const pk = this.keyStore.getPrivateKey();
		const opts = {
			message: m,
			privateKeys: [pk],
			detached: true,
		}
		pgp.sign(opts).then((s) => {
			this.signature = {
				engine: this.engine,
				algo: this.algo,
				data: s.signature,
				// TODO: fix for browser later
				digest: digest,
			};
			this.onsign(this.signature);
		}).catch((e) => {
			console.error(e);
			this.onsign(undefined);
		});
	}
}

export {
	Signature,
	Authoritative,
       	Signer,
	KeyGetter,
	Signable,
	KeyStore,
	PGPSigner,
	PGPKeyStore,
};

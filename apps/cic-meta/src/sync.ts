import * as Automerge from 'automerge';

import { JSONSerializable } from './format';

import { Authoritative, Signer, PGPSigner, Signable, Signature } from './auth';

import { engineSpec, cryptoSpec, networkSpec, VersionedSpec  } from './constants';

const fullSpec:VersionedSpec = {
	name: 'cic',
	version: '1',
	ext: {
		network: cryptoSpec,
		engine: engineSpec,
	},
}

class Envelope {

	o = fullSpec

	constructor(payload:Object) {
		this.set(payload);
	}

	public set(payload:Object) {
		this.o['payload'] = payload
	}

	public get():string {
		return this.o['payload'];
	}

	public toJSON() {
		return JSON.stringify(this.o);
	}

	public static fromJSON(s:string): Envelope {
		const e = new Envelope(undefined);
		e.o = JSON.parse(s);
		return e;
	}

	public unwrap(): Syncable {
		return Syncable.fromJSON(this.o['payload']);
	}
}

class ArgPair {

	k:string
	v:any

	constructor(k:string, v:any) {
		this.k = k;
		this.v = v;
	}
}

class SignablePart implements Signable {

	s: string

	constructor(s:string) {
		this.s = s;
	}

	public digest():string {
		return this.s;
	}
}

function orderDict(src) {
	let dst;
	if (Array.isArray(src)) {
		dst = [];
		src.forEach((v) => {
			if (typeof(v) == 'object') {
				v = orderDict(v);
			}
			dst.push(v);
		});
	} else {
		dst = {}
		Object.keys(src).sort().forEach((k) => {
			let v = src[k];
			if (typeof(v) == 'object') {
				v = orderDict(v);
			}
			dst[k] = v;
		});
	} 
	return dst;
}

class Syncable implements JSONSerializable, Authoritative {

	id:		string
	timestamp:	number
	m:		any // automerge object
	e:		Envelope
	signer:		Signer
	onwrap: 	(string) => void
	onauthenticate:	(boolean) => void

	// TODO: Move data to sub-object so timestamp, id, signature don't collide
	constructor(id:string, v:Object) {
		this.id = id;
		const o = {
			'id': id,
			'timestamp': Math.floor(Date.now() / 1000),
			'data': v,
		}
		//this.m = Automerge.from(v)
		this.m = Automerge.from(o)
	}

	public setSigner(signer:Signer) {
		this.signer = signer;
		this.signer.onsign = (s) => {
			this.wrap(s);
		};
	}

	// TODO: To keep integrity, the non-link key/value pairs for each step also need to be hashed
	public digest(): string {
		const links = [];
		Automerge.getAllChanges(this.m).forEach((ch:Object) => {
			const op:Array<any> = ch['ops'];
			ch['ops'].forEach((op:Array<Object>) => {
				if (op['action'] == 'link') {
					//console.log('op link', op);
					links.push([op['obj'], op['value']]);
				}
			});
		});
		//return JSON.stringify(links);
		const j = JSON.stringify(links);
		return Buffer.from(j).toString('base64');
	}

	private wrap(s:any) {
		this.m = Automerge.change(this.m, 'sign', (doc) => {
			doc['signature'] = s;
		});
		this.e = new Envelope(this.toJSON());
		console.log('wrappin s', s, typeof(s));
		this.e.o['digest'] = s.digest;
		if (this.onwrap !== undefined) {
			this.onwrap(this.e);
		}

	}

//	private _verifyLoop(i:number, history:Array<any>, signable:Signable, result:boolean) {
//		if (!result) {
//			this.onauthenticate(false);
//			return;
//		} else if (history.length == 0) {
//			this.onauthenticate(true);
//			return;
//		}
//		const h = history.shift()
//		if (i % 2 == 0) {
//			i++;
//			signable = {
//				digest: () => {
//					return Automerge.save(h.snapshot)
//				},
//			};
//			this._verifyLoop(i, history, signable, true);
//		} else {
//			i++;
//			const signature = h.snapshot['signature'];
//			console.debug('signature', signature, signable.digest());
//			this.signer.onverify = (v) => {
//				this._verifyLoop(i, history, signable, v)
//			}
//			this.signer.verify(signable, signature);
//		}
//	}
//
//	// TODO: This should replay the graph and check signatures on each step
//	public _authenticate(full:boolean=false) {
//		let h = Automerge.getHistory(this.m);
//		h.forEach((m) => {
//			//console.debug(m.snapshot);
//		});
//		const signable = {
//			digest: () => { return '' },
//		}
//		if (!full) {
//			h = h.slice(h.length-2);
//		}
//		this._verifyLoop(0, h, signable, true);
//	}

	public authenticate(full:boolean=false) {
		if (full) {
			console.warn('only doing shallow authentication for now, sorry');			
		}
		//console.log('authenticating', signable.digest());
		//console.log('signature', this.m.signature);
		this.signer.onverify = (v) => {
			//this._verifyLoop(i, history, signable, v)
			this.onauthenticate(v);
		}
		this.signer.verify(this.m.signature.digest, this.m.signature);
	}


	public sign() {
		//this.signer.prepare(this);
		this.signer.sign(this.digest());
	}

	public update(changes:Array<ArgPair>, changesDescription:string) {
		this.m = Automerge.change(this.m, changesDescription, (m) => {
			changes.forEach((c) => {
				let path = c.k.split('.');
				let target = m['data'];
				while (path.length > 1) {
					const part = path.shift();
					target = target[part];
				}
				target[path[0]] = c.v;
			});
			m['timestamp'] = Math.floor(Date.now() / 1000);
		});
	}

	public replace(o:Object, changesDescription:string) {
		this.m = Automerge.change(this.m, changesDescription, (m) => {
			Object.keys(o).forEach((k) => {
				m['data'][k] = o[k];
			});
			Object.keys(m).forEach((k) => {
				if (o[k] == undefined) {
					delete m['data'][k];
				}
			});
			m['timestamp'] = Math.floor(Date.now() / 1000);
		});
	}

	public merge(s:Syncable) {
		this.m = Automerge.merge(s.m, this.m);
	}

	public toJSON(): string {
		const s = Automerge.save(this.m);
		const o = JSON.parse(s);
		const oo = orderDict(o)
		return JSON.stringify(oo);

	}

	public static fromJSON(s:string): Syncable {
		const doc = Automerge.load(s);
		let y = new Syncable(doc['id'], {});
		y.m = doc
		return y
	}
}

export { JSONSerializable, Syncable, ArgPair, Envelope };

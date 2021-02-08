import * as crypto from 'crypto';

import { Signable, Signature, KeyStore } from '../src/auth';
import { Store } from '../src/store';
import { PubSub, SubConsumer } from '../src/transport';
import { Syncable } from '../src/sync';

class MockStore implements Store {
	
	contents:	Object
	name:		string

	constructor(name:string) {
		this.name = name;
		this.contents = {};
	}

	public put(k:string, v:Syncable, existsOk = false) {
		if (!existsOk && this.contents[k] !== undefined) {
			throw '"' + k + '" already exists in store ' + this.name;
		} 
		this.contents[k] = v;
	}

	public get(k:string): Syncable {
		return this.contents[k];
	}

	public delete(k:string) {
		delete this.contents[k];
	}
}

class MockSigner {
	onsign: (string) => void
	onverify: (boolean) => void
	public verify(src:string, signature:Signature) {
		return true;
	}

	public sign(s:string):boolean {
		this.onsign('there would be a signature here');
		return true;
	}

	public prepare(m:Signable):boolean {
		return true;
	}

	public fingerprint():string {
		return '';
	}
}

class MockConsumer implements SubConsumer {

	omnoms:	Array<string>

	constructor() {
		this.omnoms = Array<string>();
	}

	public post(v:string) {
		this.omnoms.push(v);
	}
}

class MockPubSub implements PubSub {

	pubs:		Array<string>
	consumer:	SubConsumer

	constructor(name:string, consumer:SubConsumer) {
		this.pubs = Array<string>();	
		this.consumer = consumer;
	}
	
	public pub(v:string): boolean {
		this.pubs.push(v);
		return true;
	}

	public flush() {
		while (this.pubs.length > 0) {
			const s = this.pubs.shift();
			this.consumer.post(s);
		}
	}

	public close() {
	}
}

class MockSignable implements Signable {

	src:	string
	dst:	string

	constructor(src:string) {
		this.src = src;
	}

	public digest():string {
		const h = crypto.createHash('sha256');
		h.update(this.src);
		this.dst= h.digest('hex');
		return this.dst;
	}

}

class MockKeyStore implements KeyStore {

	pk: any
	pubks: Array<any>

	constructor(pk:any, pubks:Array<any>) {
		this.pk = pk;
		this.pubks = pubks;	
	}

	public getPrivateKey(): any {
		return this.pk;
	}

	public getTrustedKeys(): Array<any> {
		return this.pubks;
	}

	public getTrustedActiveKeys(): Array<any> {
		return [];
	}

	public getEncryptKeys(): Array<any> {
		return [];
	}

	public getFingerprint(): string {
		return '';
	}
}

export {
	MockStore,
	MockPubSub,
	MockConsumer,
	MockSignable,
	MockKeyStore,
	MockSigner,
};

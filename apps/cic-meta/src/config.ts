import * as fs from 'fs';
import * as ini from 'ini';
import * as path from 'path';

class Config {

	filepath: 	string
	store:		Object
	censor:		Array<string>
	require:	Array<string>
	env_prefix:	string

	constructor(filepath:string, env_prefix?:string) {
		this.filepath = filepath;
		this.store = {};
		this.censor = [];
		this.require = [];
		this.env_prefix = '';
		if (env_prefix !== undefined) {
			this.env_prefix = env_prefix + "_";
		}
	}

	public process() {
		const d = fs.readdirSync(this.filepath);
		
		const r = /.*\.ini$/;
		for (let i = 0; i < d.length; i++) {
			const f = d[i];
			if (!f.match(r)) {
				return;
			}

			const fp = path.join(this.filepath, f);
			const v = fs.readFileSync(fp, 'utf-8');
			const inid = ini.decode(v);
			const inik = Object.keys(inid);
			for (let j = 0; j < inik.length; j++) {
				const k_section = inik[j]
				const k = k_section.toUpperCase();
				Object.keys(inid[k_section]).forEach((k_directive) => {
					const kk = k_directive.toUpperCase();
					const kkk = k + '_' + kk;

					let r = inid[k_section][k_directive];
					const k_env = this.env_prefix + kkk
					const env = process.env[k_env];
					if (env !== undefined) {
						console.debug('Environment variable ' + k_env + ' overrides ' + kkk);
						r = env;
					}
					this.store[kkk] = r;
				});
			}
		}
	}

	public get(s:string) {
		return this.store[s];
	}

	public toString() {
		let s = '';
		Object.keys(this.store).forEach((k) => {
			s += k + '=' + this.store[k] + '\n';
		});
		return s;
	}	
}

export { Config };

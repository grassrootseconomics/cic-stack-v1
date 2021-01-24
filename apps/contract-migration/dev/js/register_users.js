const fs = require('fs');
const path = require('path');
const cic = require('cic-client-meta');
const http = require('http');
const confini = require('confini');

console.debug('sorry this script doesnt read cli flags, set all in env vars');

let config_data_dir = process.env.CONFINI_DIR;
if (config_data_dir === undefined) {
	config_data_dir = '/usr/local/etc/cic';
}
const config = new confini.Config(config_data_dir, process.env.CONFINI_ENV_PREFIX);
config.process();
Object.keys(config.store).forEach((k) => {
	console.debug(k, config.get(k));
});

// flatten file list from directories recursively
// cheekily though gratefully stolen from https://coderrocketfuel.com/article/recursively-list-all-the-files-in-a-directory-using-node-js 
const getAllFiles = function(dirPath, arrayOfFiles) {
  files = fs.readdirSync(dirPath)

  arrayOfFiles = arrayOfFiles || []

  files.forEach(function(file) {
    if (fs.statSync(dirPath + "/" + file).isDirectory()) {
      arrayOfFiles = getAllFiles(dirPath + "/" + file, arrayOfFiles)
    } else {
      arrayOfFiles.push(path.join(dirPath, "/", file))
    }
  })

  return arrayOfFiles
}

async function sendit(uid, envelope) {
	const d = envelope.toJSON();

	const opts = {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Content-Length': d.length,
			'X-CIC-AUTOMERGE': 'client',

		},
	};
	let url = config.get('META_PROVIDER'); //['archiveUrl'];
	url = url.replace(new RegExp('^(.+://[^/]+)/*$'), '$1/');
	const req = http.request(url + uid, opts, (res) => {
		res.on('data', process.stdout.write);
		res.on('end', () => {
			console.log('result', res.statusCode, res.headers);
		});
	});

	req.write(d);
	req.end();
}

function doit(keystore) {
	dataDir = 'data';
	if (process.argv.length > 2) {
		dataDir = process.argv[2];
	}
	console.log('argv', process.argv);
	console.log('datadir', path.join(dataDir, 'person'));
	getAllFiles(path.join(dataDir, 'person')).forEach((filename) => {
		console.debug('person file', filename);
		const signer = new cic.PGPSigner(keystore);
		const parts = filename.split('.');
		const uid = path.basename(parts[0]);
		
		const d = fs.readFileSync(filename, 'utf-8');
		const o = JSON.parse(d);

		const s = new cic.Syncable(uid, o);
		console.log(s);
		s.setSigner(signer);
		s.onwrap = (env) => {
			console.log('env', env);
			//console.log('sign', s.m.signature.digest);
			sendit(uid, env);
		};
		s.sign();
	});
}

pk = fs.readFileSync(path.join(config.get('PGP_EXPORTS_DIR'), config.get('PGP_PRIVATEKEY_FILE')));
pubk = fs.readFileSync(path.join(config.get('PGP_EXPORTS_DIR'), config.get('DEV_PGP_PUBLICKEYS_ACTIVE_FILE')));

new cic.PGPKeyStore(
	process.env['PGP_PASSPHRASE'],
	pk,
	pubk,
	undefined,
	undefined,
	doit,
);


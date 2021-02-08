const args = require('yargs');

const standardArgs = args.option('config', {
	alias: 'c',
	type: 'string',
	description: 'absolute path to configuation files directory', 

}).option('env-prefix', {
	type: 'string',
	description: 'prefix to add to environment variables to match configuration directives',

}).option('database-engine', {
	type: 'string',
	description: 'database engines to use', 

}).option('address', {
	alias: 'a',
	type: 'string',
	description: 'ip address to bind server to',

}).option('server-address', {
	alias: 'p',
	type: 'number',
	description: 'port to bind server to',

});

export { standardArgs };

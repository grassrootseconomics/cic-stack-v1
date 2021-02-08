var webpack = require('webpack');
const path = require('path');

module.exports = {
  entry: {
    index: './dist/index.js',
  },
  output: {
    path: path.resolve(__dirname, 'dist-web'),
    filename: 'cic-meta.web.js',
    library: 'cicMeta',
    libraryTarget: 'window'
  },
  mode: 'development',
  performance: {
    hints: false
  },
  stats: 'errors-only',
  resolve: {
	  fallback: {
		  "crypto": false,
	  },
  },
};

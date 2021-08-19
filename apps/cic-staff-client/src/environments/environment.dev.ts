import { NgxLoggerLevel } from 'ngx-logger';

export const environment = {
  production: false,
  bloxbergChainId: 8996,
  logLevel: NgxLoggerLevel.DEBUG,
  serverLogLevel: NgxLoggerLevel.OFF,
  loggingUrl: '',
  cicMetaUrl: 'http://localhost:63380',
  publicKeysUrl: 'https://dev.grassrootseconomics.net/.well-known/publickeys/',
  cicCacheUrl: 'http://localhost:63313',
  web3Provider: 'http://localhost:8545',
  cicUssdUrl: 'http://localhost:63415',
  registryAddress: '0xea6225212005e86a4490018ded4bf37f3e772161',
  trustedDeclaratorAddress: '0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C',
  dashboardUrl: 'https://dashboard.sarafu.network/',
};

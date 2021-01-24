#!/bin/bash

cic_data_dir=${CIC_DATA_DIR:-/tmp/cic}
t=${1:-$(mktemp)}
prefix=''
if [ ! -z $2 ]; then
	prefix="${2}_"
fi

echo "#!/bin/bash" > $t
echo "set +a" >> $t
cat $cic_data_dir/.env | sed -e "s/^\([A-Z]\)/export ${prefix}\1/g" >> $t

#if [ -f $cic_data_dir/.env ]; then
#cat $cic_data_dir/.env | sed -e "s/^\([A-Z]\)/export ${prefix}\1/g"  >> $t
#fi
echo "export CONFINI_DIR=$(dirname $(realpath .))/config_template" >> $t
source $t
echo "export CELERY_BROKER_URL=redis://localhost:${HTTP_PORT_REDIS}" >> $t
echo "export CELERY_RESULT_URL=redis://localhost:${HTTP_PORT_REDIS}" >> $t
echo "export ETH_PROVIDER=http://localhost:${HTTP_PORT_ETH}" >> $t
echo "export META_PROVIDER=http://localhost:${HTTP_PORT_CIC_META}" >> $t
echo "set -a" >> $t
echo $t

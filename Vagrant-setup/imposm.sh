wget --quiet -O imposm3.tar.gz  http://imposm.org/static/rel/imposm3-0.1dev-20140811-3f3c12e-linux-x86-64.tar.gz
mkdir imposm3
tar -zxf imposm3.tar.gz -C imposm3 --strip-components=1
rm imposm3.tar.gz

#!/bin/bash

rm -fr temp-certs
mkdir temp-certs

if [ -z $PREFIX ] ; then
    PREFIX=dev-authdb-
fi

cp ${PREFIX}server-ca.pem temp-certs/server-ca.pem
cp ${PREFIX}client-cert.pem temp-certs/client-cert.pem
cp ${PREFIX}client-key.pem temp-certs/client-key.pem
#
# Using client-key.pem fails. This is likely PEM is unsupported for client key.
openssl pkcs8 -topk8 -inform PEM -outform DER -in ${PREFIX}client-key.pem -out temp-certs/client-key.key -nocrypt

OUTPUT=${PREFIX}db-certs-expand.sh

echo "#!/bin/sh" > $OUTPUT
echo "cat > server-ca.pem << EOF" >> $OUTPUT
cat temp-certs/server-ca.pem >> $OUTPUT
echo "" >> $OUTPUT
echo "EOF" >> $OUTPUT

echo "cat > client-cert.pem << EOF" >> $OUTPUT
cat temp-certs/client-cert.pem >> $OUTPUT
echo "" >> $OUTPUT
echo "EOF" >> $OUTPUT

echo "cat > client-key.pem << EOF" >> $OUTPUT
cat temp-certs/client-key.pem >> $OUTPUT
echo "" >> $OUTPUT
echo "EOF" >> $OUTPUT

echo "cat > client-key.key.b64 << EOF" >> $OUTPUT
base64 temp-certs/client-key.key >> $OUTPUT
echo "" >> $OUTPUT
echo "EOF" >> $OUTPUT

echo 'base64 -d client-key.key.b64 > client-key.key' >> $OUTPUT

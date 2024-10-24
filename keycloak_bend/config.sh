#!/bin/bash

if [ -r .env ] ; then
  . .env
else
  echo DB_ADDR_PUBLIC=$(op item get wos2wdt56jx2gjmvb4awlxk3ay --format=json | jq -r '.fields[] | select(.id == "fnxbox5ugfkr2ol5wtqbk6wkwq") | .value') >> .env
  echo DB_ADDR_PRIVATE=$(op item get wos2wdt56jx2gjmvb4awlxk3ay --format=json | jq -r '.fields[] | select(.id == "o4idffxy6bns7nihak4q4lo3xe") | .value') >> .env
  echo DB_USER=keycloak >> .env
  echo DB_PASS=$(op item get wos2wdt56jx2gjmvb4awlxk3ay --format=json | jq -r '.fields[] | select(.id == "vlf6422dpbnqhne535fpgg4vqm") | .value') >> .env
  echo KC_ADMIN_PASSWORD=$(op item get bdmmxlepkfsqy5hfgfunpsli2i --format=json | jq -r '.fields[] | select(.id == "password") | .value') >> .env
fi

if [ -z $1 ] ; then
  cat .env
else
  gawk -F = -e "/^$1=/ {print substr(\$0,length(\" $1=\"),999)}" .env
fi

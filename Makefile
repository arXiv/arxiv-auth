
bootstrap: .bootstrap

.bootstrap:
	gh extension install https://github.com/nektos/gh-act
	touch .bootstrap

test:
	gh act

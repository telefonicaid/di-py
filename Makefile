
release:
ifndef VERSION
	$(error VERSION is undefined)
endif
	# Please install twine (`pip install twine`)
	# in order to use https instead of http
	# to upload a new version to pypi.
	#
	# https://twitter.com/glyph/status/580796504215924736
	# https://pypi.python.org/pypi/twine

	git checkout -b ${VERSION}-release master

	sed -i '' -e "s/version='[^']*'/version='${VERSION}'/" setup.py
	git add setup.py
	git commit -m "Tagging version ${VERSION}"

	git tag ${VERSION}
	git push origin ${VERSION}

	# Package and upload to pypi
	rm -rf dist && python setup.py sdist && twine upload dist/*

	# Bring new version to master
	git checkout master
	git merge --ff ${VERSION}-release
	git push origin master
	git branch -D ${VERSION}-release

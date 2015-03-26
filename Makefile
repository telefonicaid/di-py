
release:
ifndef VERSION
	$(error VERSION is undefined)
endif
	pip install twine

	git checkout -b ${VERSION}-release master

	sed -i '' -e 's/{VERSION}/${VERSION}/g' setup.py
	git add setup.py
	git commit -m "Tagging version ${VERSION}"

	git tag ${VERSION}
	git push origin ${VERSION}

	# Package and upload to pypi
	rm -rf dist && python setup.py sdist && twine upload dist/*

	git checkout master
	git branch -D ${VERSION}-release

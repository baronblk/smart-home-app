.PHONY: css
css:
	npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/tailwind.css --minify

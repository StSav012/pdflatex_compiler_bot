# pdflatex_compiler_bot

This Telegram bot gets ZIP archives containing full LaTeX projects and tries to build a PDF file based on their content.

The LaTeX compiler and the bibliography tool can be set manually. Append file called `bot.ini` to the archive you send.
The file should look like the following:
```ini
[commands]
compiler = pdflatex
bibliography = bibtex
``` 
The compiler should be one of `latex`, `pdflatex`, `xetex`, or `lualatex`;
the bibliography tool may be `bibtex`, `bibtex8`, or `biber`.
The default values are shown above. They will be used as fallback ones if no valid values are provided. 

I do not promise that the bot is always online. Moreover, I encourage you to clone the repo and run the bot on your
machine, for I can not spend all my computer power to others' needs. My PC is just not fast enough to serve everyone.
Therefore, I do not provide you with a link.

"""
    gpytranslate - A Python3 library for translating text using Google Translate API.
    MIT License

    Copyright (c) 2021 Davide Galilei

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""

from collections.abc import Mapping
from typing import Union, Dict, List, Any, BinaryIO

import httpx

from ..types import TranslatedObject, BaseTranslator, BASE_HEADERS


class SyncTranslator(BaseTranslator):
    def __init__(
        self,
        proxies: Dict[str, str] = None,
        url: str = "https://translate.googleapis.com/translate_a/single",
        tts_url: str = "https://translate.google.com/translate_tts",
        headers: dict = ...,
        **options
    ):
        self.url = url
        self.tts_url = tts_url
        self.proxies = proxies
        self.options = options
        self.headers = BASE_HEADERS if headers is Ellipsis else headers

    def translate(
        self,
        text: Union[str, List[str], Dict[Any, str], Mapping],
        sourcelang: str = "auto",
        targetlang: str = "en",
        client: str = "gtx",
        dt: str = "t",
        dj: int = 1,
        **extra
    ) -> Union[TranslatedObject, List[TranslatedObject], Dict[str, TranslatedObject]]:

        """
        A function that translates text.

        Parameters:
            text: str = Text to translate.


            sourcelang: str = "text" original language, pass "auto" for auto detection (default: "auto").


            targetlang: str = target language for translating "text" (default: "en").


            client: str = Google Translate client platform I guess, it's not well documented. (default: "gtx")
                (Will return the raw API json if "client" is not "gtx")


            dt: str = Specifies what to return in the API reply (default: "t").
                (Will return the raw API json if "dt" is not "t".
                t - Translation of source text;
                at - Alternate translations;
                rm - Transcription / transliteration of source and translated texts;
                bd - Dictionary, in case source text is one word
                     (you get translations with articles, reverse translations, etc.);
                md - Definitions of source text, if it's one word;
                ss - Synonyms of source text, if it's one word;
                ex - Examples;
                rw - See also list;
                dj - Json response with names. (dj=1).)

            dj: int = Probably specifies dictionary output if true, else list (default: 1).

            extra: dict = Extra params to be sent to api endpoint.

        Returns:
            TranslatedObject or JSON serialized object.
        """

        params = {
            k: v
            for k, v in {
                "client": client,
                "sl": sourcelang,
                "tl": targetlang,
                "dt": dt,
                "ie": "utf-8",
                "oe": "utf-8",
                "dj": dj,
                **extra,
            }.items()
            if v is not None
        }
        with httpx.Client(proxies=self.proxies, **self.options) as c:
            raw: Union[Mapping, List] = (
                c.post(
                    self.url,
                    params={**params, "q": text},
                    headers=self.headers,
                ).json()
                if isinstance(text, str)
                else (
                    {
                        k: c.post(
                            self.url,
                            params={**params, "q": v},
                            headers=self.headers,
                        ).json()
                        for k, v in text.items()
                    }
                    if isinstance(text, Mapping)
                    else [
                        c.post(
                            self.url,
                            params={**params, "q": elem},
                            headers=self.headers,
                        ).json()
                        for elem in text
                    ]
                )
            )
            c.close()

        return self.check(raw=raw, client=client, dt=dt, text=text)

    def detect(self, text: Union[str, list, dict]):
        if isinstance(text, str):
            return self(text).lang
        elif isinstance(text, list):
            return [self(elem).lang for elem in text]
        elif isinstance(text, dict):
            return {k: self(v).lang for k, v in text.items()}
        else:
            raise ValueError("Language detection works only with str, list and dict")

    def tts(
        self,
        text: Union[str, List[str], Dict[Any, str], Mapping],
        file: BinaryIO,
        targetlang: str = "en",
        client: str = "at",
        idx: int = 0,
        prev: str = "input",
        chunk_size: int = 1024,
        textlen: int = None,
        **extra
    ) -> BinaryIO:
        params = self.parse_tts(
            client=client,
            targetlang=targetlang,
            idx=idx,
            prev=prev,
            text=text,
            textlen=textlen,
            extra=extra,
        )
        with httpx.stream(
            "GET",
            url=self.tts_url,
            params=params,
            headers=self.headers,
        ) as response:
            response: httpx.Response
            for chunk in response.iter_bytes(chunk_size=chunk_size):
                file.write(chunk)
        return file

    __call__ = translate

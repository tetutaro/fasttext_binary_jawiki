# fasttext_binary_jawiki

日本語 Wikipedia を学習した [fastText](https://github.com/facebookresearch/fastText)（単語分散表現）のバイナリを作る

## 特徴

* Wikimedia の CirrusSearch ダンプページをクローリングし、最新の日本語 Wikipedia のダンプを自動で取ってくる
* 軽量で使いやすい gensim.models.KeyedVector のバイナリに変換

## 前提

* MeCab 用の辞書がインストールされている
    * [mecab_dictionaries](https://github.com/tetutaro/mecab_dictionaries) で作った `unidic_cwj-3.1.1-py3-none-any.whl` がインストールされていることを想定しています
* 必要な Python パッケージは [requirements.txt](requirements.txt) を参照
    * 上記 MeCab 辞書以外

## 注意

- 日本語Wikipediaの全ページを前処理し学習するので、とても時間がかかります
    - 古めのマシンだと本当に１日ぐらいかかる
- 空き容量もそこそこ必要です
    - 15GBぐらいは使うかも

## コーパスの作り方

日本語 Wikipedia のダンプをダウンロードし、コーパスを作る。

```
usage: create_corpus_jawiki.py [-h] [-v YYYYMNMDD] [-b]

create corpus from Japanese Wikipedia

options:
  -h/--help              show this help message and exit
  -v/--version YYYYMMDD  Wikipedia version
  -b, --base             use base form
```

* 特定の Wikipedia のバージョンを指定したい場合は、`--version YYYYMMDD` の形で与える
* 変化形のある単語を全て原形（base form）に直したい場合は、`--base` オプションを付ける

## fastText の 日本語 Wikipedia 学習済みバイナリの作り方

`create_corpus_jawiki.py` で `jawiki[_base]_YYYYMMDD.txt` というコーパスが出来るので、それを学習して作る。

```
usage: create_fasttext_binary.py [-h] [-m {skipgram,cbow}] [--dim DIM]
                                 [--epoch EPOCH] [--mincount MINCOUNT]
                                 CORPUS

train the corpus and create word2vec format binary

positional arguments:
  CORPUS                curpus file

options:
  -h/--help             show this help message and exit
  -m/--model {skipgram,cbow}
                        data representation model in fastText
                        (default: skipgram)
  --dim DIM             size of word vectors (default: 200)
  --epoch EPOCH         number of training epochs (default: 10)
  --mincount MINCOUNT   minimal number of word occurrences (default: 20)
```

## 学習済みバイナリ

`kv_fasttext_jawiki[_base]_YYYYMMDD.bin` が目的のバイナリです。
`gensim.models.keyedvectors.KeyedVectors` の `load_word2vec_format()` でロードして使って下さい。

その他にも以下のものが作られますが、問題が発生したときに途中から再開できるように残してあるだけなので、ディスク容量が気になる場合は削除してください。

* `jawiki-YYYYMMDD-pages-articles-multistream.xml.bz2`
    * 日本語 Wikipedia のダンプ
* `jawiki_YYYYMMDD/`
    * 上記を [WikiExtractor](https://github.com/zaemyung/wikiextractor) で展開したもの
* `temp[_base]_jawiki_YYYYMMDD/`
    * WikiExtractor で展開した各ファイルの内容を分かち書きしたもの
* `jawiki[_base]_YYYYMMDD.txt`
    * コーパス
* `fasttext_jawiki[_base]_YYYYMMDD.bin`
    * 学習した fastText のバイナリ
* `fasttext_jawiki[_base]_YYYYMMDD.vec`
    * 学習した単語ベクトルを word2vec 形式で書き下したもの

## サンプル実装

```
usage: w2v.py [-h] [-n [NEG ...]] [-v YYYYMMDD] [--topn TOPN] [-b] POS [POS ...]

find the word that have similar meanings

positional arguments:
  POS                   word[s] that contribute positively

options:
  -h/--help             show this help message and exit
  -n/--neg [NEG ...]    word[s] that contribute negatively
  -v/--version YYYYMMDD version of trained binary
  --topn TOPN           number of top-N words to display (default: 5)
  -b/--base             use base form
```

pos や neg に学習済みでない単語を指定すると、それは除外します。
また pos として学習済みの単語をひとつ以上指定しないとエラーになります。

変化形を原形に変換して学習したものを使いたい場合は `-b` オプションを付けてください。

### 例

「フロンターレ」に近い意味の単語 Top 10

```
> ./w2v.py -b フロンターレ --topn 10
kv_fasttext_jawiki_base_20230101.bin: 200 dimension 215263 vectors
positives: ['フロンターレ'], negatives: None
【結果】
1. ベルマーレ : 0.8110328912734985
2. トリニータ : 0.8010317087173462
3. アントラーズ : 0.7997881770133972
4. レイソル : 0.799777626991272
5. マリノス : 0.7983289361000061
6. アルディージャ : 0.796067476272583
7. ヴィッセル : 0.783135712146759
8. ヴァンフォーレ : 0.7786958813667297
9. セレッソ : 0.7717006802558899
10. アビスパ : 0.7642964124679565
```

「水泳」＋「バイク」＋「マラソン」に近い意味の単語 Top 5

```
> ./w2v.py -b 水泳 バイク マラソン
kv_fasttext_jawiki_base_20230101.bin: 200 dimension 215263 vectors
positives: ['水泳', 'バイク', 'マラソン'], negatives: None
【結果】
1. トライアスロン : 0.7762919664382935
2. 競技 : 0.7312951683998108
3. ＢＭＸ : 0.7160383462905884
4. セーリング : 0.7083388566970825
5. スケートボード : 0.7082747220993042
```

「王」−「男」＋「女」に近い意味の単語 Top 5

```
> ./w2v.py -b 王 女 -n 男
kv_fasttext_jawiki_base_20230101.bin: 200 dimension 215263 vectors
positives: ['王', '女'], negatives: ['男']
【結果】
1. 王妃 : 0.5966609120368958
2. 女王 : 0.5590444803237915
3. 王女 : 0.5498331785202026
4. 新王 : 0.5435934662818909
5. 妃 : 0.5255797505378723
```

「右腕」−「右」＋「左」に近い意味の単語 Top 5

```
> ./w2v.py -b 右腕 左 -n 右
kv_fasttext_jawiki_base_20230101.bin: 200 dimension 215263 vectors
positives: ['右腕', '左'], negatives: ['右']
【結果】
1. 左腕 : 0.8250712156295776
2. 片腕 : 0.727178692817688
3. 手首 : 0.6932733058929443
4. 両腕 : 0.6921244263648987
5. 腕 : 0.6593101620674133
```

「札幌」−「東京」＋「大阪」に近い意味の単語 Top 5

```
> ./w2v.py -b 札幌 大阪 -n 東京
kv_fasttext_jawiki_base_20230101.bin: 200 dimension 215263 vectors
positives: ['札幌', '大阪'], negatives: ['東京']
【結果】
1. 旭川 : 0.6767386198043823
2. 帯広 : 0.6556068658828735
3. 岩見沢 : 0.6257429122924805
4. 吹田 : 0.6097605228424072
5. さっぽろ : 0.6018339395523071
```

「俳優」−「男」＋「女」に近い意味の単語 Top 5

```
> ./w2v.py -b 俳優 女 -n 男
kv_fasttext_jawiki_base_20230101.bin: 200 dimension 215263 vectors
positives: ['俳優', '女'], negatives: ['男']
【結果】
1. 女優 : 0.7013211846351624
2. 子役 : 0.6389188766479492
3. 声優 : 0.6049207448959351
4. 新劇 : 0.6039800047874451
5. 歌手 : 0.5910342335700989
```

「よさこい」−「高知」＋「札幌」に近い意味の単語 Top 5

```
> ./w2v.py -b よさこい 札幌 -n 高知
kv_fasttext_jawiki_base_20230101.bin: 200 dimension 215263 vectors
positives: ['よさこい', '札幌'], negatives: ['高知']
【結果】
1. ＹＯＳＡＫＯＩ : 0.5842196345329285
2. ソーラン : 0.5661107301712036
3. 雪まつり : 0.565356969833374
4. さっぽろ : 0.5364177823066711
5. すずめ踊り : 0.5175777077674866
```

「放送」−「電波」＋「インターネット」に近い意味の単語 Top 5

```
> ./w2v.py -b 放送 インターネット -n 電波
kv_fasttext_jawiki_base_20230101.bin: 200 dimension 215263 vectors
positives: ['放送', 'インターネット'], negatives: ['電波']
【結果】
1. 配信 : 0.6678400635719299
2. ネット : 0.6672139167785645
3. 番組 : 0.6619077324867249
4. Ustream : 0.6312112212181091
5. サイマル : 0.6299905180931091
```

# fasttext_binary_jawiki

日本語 Wikipedia を学習した [fastText](https://github.com/facebookresearch/fastText)（単語分散表現）のバイナリを作る

## 特徴

- Wikimedia をクローリングし、最新の日本語 Wikipedia のダンプを自動で取ってくる
- 軽量で使いやすい gensim.models.KeyedVector のバイナリに変換

## 前提

- MeCab がインストールされている
- MeCab 用の辞書が用意されている
- 必要な Python パッケージは [requirements.txt](requirements.txt) を参照のこと

## 注意

- 日本語Wikipediaの全ページを前処理し学習するので、とても時間がかかります
    - 古めのマシンだと本当に１日ぐらいかかる
- 空き容量もそこそこ必要です
    - 15GBぐらいは使うかも

## 作り方

```
usage: create_fasttext_binary.py [-h] [-d DICTIONARY] [-o]
                                 [-m {skipgram,cbow}] [--dim DIM]
                                 [--epoch EPOCH] [--mincount MINCOUNT]

tokenize sentence into morphemes using MeCab

optional arguments:
  -h, --help            show this help message and exit
  -d DICTIONARY, --dictionary DICTIONARY
                        path of MeCab dictonary or [ipa|juman|neologd]
  -o, --original        use original form
  -m {skipgram,cbow}, --model {skipgram,cbow}
                        data representation model in fastText (default:
                        skipgram)
  --dim DIM             size of word vectors (default: 300)
  --epoch EPOCH         number of training epochs (default: 10)
  --mincount MINCOUNT   minimal number of word occurrences (default: 20)
```

変化形を原形に変換して学習したい場合は `-o` オプションを付けてください。

## MeCab 辞書

お薦めは(私のrepository)[https://github.com/tetutaro/mecab_dictionary]を使うことです。
上記の repository を clone し、説明に従って辞書を作り、
そうして出来た `mecab_ipadic` ディレクトリを、ここにシンボリックリンクを張るなり移動するなりコピーするなりしてください。
この場合、`-d` オプションを指定しなくても認識します。

それ以外の場合は、MeCab 辞書のパスを指定するか、IPA 辞書・JUMAN 辞書・[IPA NEologd 辞書](https://github.com/neologd/mecab-ipadic-neologd)をインストールし、その名前（ipa, juman, neologd）を指定する必要があります。

## 生成物

`kv_fasttext_jawiki_YYYYMMDD.bin` が目的のバイナリです。
`gensim.models.keyedvectors.KeyedVectors` の `load_word2vec_format()` でロードして使って下さい。

その他にも以下のものが作られますが、問題が発生したときに途中から再開できるように残してあるだけなので、ディスク容量が気になる場合は削除してください。

- jawiki-YYYYMMDD-pages-articles-multistream.xml.bz2
    - 日本語 Wikipedia のダンプ
- jawiki_YYYYMMDD ディレクトリ
    - 上記を [WikiExtractor](https://github.com/zaemyung/wikiextractor) で展開したもの
- jawiki_YYYYMMDD.txt
    - fastText 学習用のデータ
- fasttext_jawiki_YYYYMMDD.bin
    - 学習した fastText のバイナリ
- fasttext_jawiki_YYYYMMDD.vec
    - 学習した単語ベクトルを word2vec 形式で書き下したもの

## サンプル実装

生成した `kv_fasttext_jawiki_YYYYMMDD.bin` を使って「似た意味の単語を探す」プログラムを作成しました。ご参考までに。

### 使い方

```
usage: w2v.py [-h] [-o] pos [pos ...] [-n [NEG [NEG ...]]] [--topn TOPN]

find the word that have similar meanings

positional arguments:
  pos                   word[s] that contribute positively

optional arguments:
  -h, --help            show this help message and exit
  -n [NEG [NEG ...]], --neg [NEG [NEG ...]]
                        word[s] that contribute negatively
  --topn TOPN           number of top-N words to display (default: 5)
  -o, --original        use original form
```

pos や neg に学習済みでない単語を指定すると、それは除外します。
また pos として学習済みの単語をひとつ以上指定しないとエラーになります。

変化形を原形に変換して学習したものを使いたい場合は `-o` オプションを付けてください。

### 例

「フロンターレ」に近い意味の単語 Top 10

```
> ./w2v.py フロンターレ --topn 10
【結果】
1. 川崎フロンターレ : 0.801146924495697
2. 大宮アルディージャ : 0.7202813625335693
3. FC東京 : 0.6904745697975159
4. F・マリノス : 0.6865490078926086
5. アルディージャ : 0.6861094832420349
6. 大宮アルディージャユース : 0.6827453970909119
7. 浦和レッズ : 0.6827343702316284
8. ジェフユナイテッド市原・千葉リザーブズ : 0.6774695515632629
9. ヴァンフォーレ甲府 : 0.675808846950531
10. ジュビロ磐田 : 0.6728240251541138
```

「水泳」＋「自転車」＋「マラソン」に近い意味の単語 Top 5

```
> ./w2v.py 水泳 自転車 マラソン
【結果】
1. トライアスロン : 0.7470418810844421
2. 車いすマラソン : 0.7251624464988708
3. 陸上競技 : 0.694725513458252
4. サイクリング : 0.6912835836410522
5. マウンテンバイクレース : 0.6851004362106323
```

「王」−「男」＋「女」に近い意味の単語 Top 5

```
> ./w2v.py 王 女 --neg 男
【結果】
1. 王位 : 0.6868267059326172
2. 王妃 : 0.6588720083236694
3. 国王 : 0.6583836674690247
4. 王家 : 0.6464112401008606
5. 先王 : 0.6295769810676575
```

「右腕」−「右」＋「左」に近い意味の単語 Top 5

```
> ./w2v.py 右腕 左 --neg 右
【結果】
1. 左腕 : 0.793571412563324
2. 腕 : 0.6797513961791992
3. 片腕 : 0.6668301820755005
4. 左肩 : 0.629976749420166
5. 肩 : 0.6073697805404663
```

「札幌」−「東京」＋「大阪」に近い意味の単語 Top 5

```
> ./w2v.py 札幌 大阪 --neg 東京
【結果】
1. 函館 : 0.7571847438812256
2. 帯広 : 0.7389914393424988
3. 札幌市 : 0.726713240146637
4. 小樽 : 0.7243739366531372
5. 札幌市内 : 0.712246298789978
```

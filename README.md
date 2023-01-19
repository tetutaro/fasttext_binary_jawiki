# fasttext_binary_jawiki

日本語 Wikipedia を学習した [fastText](https://github.com/facebookresearch/fastText)（単語分散表現）のバイナリを作る

## 特徴

* Wikimedia をクローリングし、最新の日本語 Wikipedia のダンプを自動で取ってくる
* 軽量で使いやすい gensim.models.KeyedVector のバイナリに変換
* [東北大学 鈴木正敏さんのサイト](http://www.cl.ecei.tohoku.ac.jp/~m-suzuki/jawiki_vector/) にあるように、日本語 Wikipedia 内へのハイパーリンクが付いている言葉は固有名詞（エンティティ）と見做し、リンク先ページのタイトルに置き換え、その言葉はひとつの形態素（単語）となるよう分割する
    * 日本語 Wikipedia 以外へのリンクは、文章そのままにする
    * 日本語 Wikipedia 内へのリンクでも、該当するページが無ければ、文章そのままにする
    * 上記サイトでは、固有名詞（エンティティ）には大括弧（`[`, `]`）を両端に付けて、一般的に文章に現れる単語と明示的に区別をしている
    * しかし、両端に大括弧を付けると、一般的な用途において非常に使いにくい
        * 明示的にエンティティと判断できた `[沖縄県]` という単語と、エンティティと判断できずに一般的な単語と判断した `沖縄県` という単語の両方が存在する可能性があり、どちらなら学習できているのか、どちらを使うべきなのかが不明
    * よって本実装では、エンティティであっても大括弧は付けない
        * `沖縄県` という言葉をそのまま使って分析することが出来、大括弧を付けるべきかどうかを迷うことは無い
    * また日本語 Wikipedia では、曖昧さの回避のために、タイトルに括弧で説明を付ける場合がある
        * 例：`スズキ (企業)` と `スズキ (魚)`
    * 上記サイトでは、エンティティである単語を、これら追加説明の括弧を付けたものに置き換えている
        * `スズキ (企業)` と `スズキ (魚)` を明確に区別することが出来るという利点がある
    * しかし、この括弧による説明の付加は、一般的な用途において非常に使いにくい
        * 文章中に現れる全ての `スズキ` を、企業なのか魚なのか（人力で）判定して付加しないと、単語分散表現（ベクトル化）が出来ない
        * そもそも、このエンティティは括弧の説明をつけるべきなのか、括弧の説明としてどのような候補があるのかを完全に把握するのは実際には不可能に近い
    * よって本実装では、括弧の説明はすべて省略する
        * `スズキ (企業)` と `スズキ (魚)` を区別できないが、一般的な用途に支障をきたすことがない
    * さらに日本語 Wikipedia では、あるページでハイパーリンクを貼った言葉が再び現れても、必ずしもその単語にもハイパーリンクを貼るとは限らない（ハイパーリンクを省略しても良い）となっている
    * 上記サイトでは、ページ内のエンティティを一旦すべて抽出し、それらを最長一致でページ内を全文探索し、見つかったものはタイトルに置換するということを行っている
    * 本実装でも、とりあえず実装はしたが、実行していない
        * ものすごく時間がかかってしまうから
        * MeCab 辞書として IPA NEologd 辞書もしくは IPA NEologd を取り込んだ IPA 辞書を使えば、Wikipedia のタイトルにある言葉は形態素として分解するはずだから

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
usage: create_fasttext_binary.py [-h] [-v VERSION] [-d DICTIONARY] [-o]
                                 [-m {skipgram,cbow}] [--dim DIM]
                                 [--epoch EPOCH] [--mincount MINCOUNT]

tokenize sentence into morphemes using MeCab

optional arguments:
  -h, --help            show this help message and exit
  -v VERSION, --version VERSION
                        indicate version of Wikipedia
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

特定の時点の Wikipedia で学習したい場合は `-v` オプションで `YYYYMMDD` を指定してください。

## MeCab 辞書

お薦めは[私のrepository](https://github.com/tetutaro/mecab_dictionary)を使うことです。
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
usage: w2v.py [-h] [-o] pos [pos ...]
              [--topn TOPN] [-v VERSION] [-n [NEG ...]]

find the word that have similar meanings

positional arguments:
  pos                   word[s] that contribute positively

optional arguments:
  -h, --help            show this help message and exit
  -o, --original        use original form
  --topn TOPN           number of top-N words to display (default: 5)
  -v VERSION, --version VERSION
                        version of trained binary
  -n [NEG ...], --neg [NEG ...]
                        word[s] that contribute negatively
```

pos や neg に学習済みでない単語を指定すると、それは除外します。
また pos として学習済みの単語をひとつ以上指定しないとエラーになります。

変化形を原形に変換して学習したものを使いたい場合は `-o` オプションを付けてください。

### 例

「フロンターレ」に近い意味の単語 Top 10

```
> ./w2v.py フロンターレ --topn 10
【結果】
1. 川崎フロンターレ : 0.7997962236404419
2. FC東京 : 0.7032252550125122
3. 大宮アルディージャ : 0.6922661066055298
4. 大宮アルディージャVENTUS : 0.6867601275444031
5. 横浜F・マリノス : 0.6845583915710449
6. ヴァンフォーレ甲府 : 0.6789917349815369
7. ジュビロ磐田 : 0.677998423576355
8. F・マリノス : 0.6743793487548828
9. 横浜FC : 0.6738860011100769
10. サガン鳥栖 : 0.6733570694923401
```

「水泳」＋「自転車」＋「マラソン」に近い意味の単語 Top 5

```
> ./w2v.py 水泳 自転車 マラソン
【結果】
1. トライアスロン : 0.7410668134689331
2. オープンウォータースイミング : 0.7090177536010742
3. 陸上競技 : 0.7036643028259277
4. サイクリング : 0.698056161403656
5. クロスカントリー競走 : 0.6872199177742004
```

「王」−「男」＋「女」に近い意味の単語 Top 5

```
> ./w2v.py 王 女 --neg 男
【結果】
1. 王位 : 0.6767063140869141
2. 王妃 : 0.6672095656394958
3. 国王 : 0.6519134640693665
4. 王家 : 0.6323437094688416
5. 先王 : 0.6142494678497314
```

「右腕」−「右」＋「左」に近い意味の単語 Top 5

```
> ./w2v.py 右腕 左 --neg 右
【結果】
1. 左腕 : 0.8022875785827637
2. 腕 : 0.6888023018836975
3. 片腕 : 0.6562961935997009
4. 左肩 : 0.6291792392730713
5. 肘 : 0.6114828586578369
```

「札幌」−「東京」＋「大阪」に近い意味の単語 Top 5

```
> ./w2v.py 札幌 大阪 --neg 東京
【結果】
1. 函館 : 0.7458642721176147
2. 帯広 : 0.7424967885017395
3. 札幌市 : 0.7378504276275635
4. 釧路 : 0.7191042304039001
5. 旭川 : 0.7135015726089478
```

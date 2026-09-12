# おつたえシート

話す直前に、まとまっていない内容を「事実・希望・確認したいこと・話す順番」に整理し、読み上げやすい短いカンペを作るStreamlitアプリです。

## できること

- 文字または音声で自由に入力
- AIによる4項目への整理
- 整理結果の編集・追加・削除
- 15秒・30秒・少し詳しいカンペの生成
- 完成したカンペの端末音声による読み上げ
- 最初からやり直し

履歴保存、Supabase、場面選択、子ども向けモードはMVP後の追加対象です。現時点では入力内容をデータベースに保存しません。

## パソコンで試す方法

1. このフォルダを開きます。
2. ターミナルで `pip install -r requirements.txt` を実行します。
3. `.streamlit/secrets.toml.example` をコピーし、名前を `secrets.toml` にします。
4. `secrets.toml` の値を自分のOpenAI APIキーに置き換えます。
5. `streamlit run app.py_ver.1.py` を実行します。

APIキーを設定しなくても、簡易整理モードで画面遷移と編集・カンペ表示を試せます。音声の文字起こしと高精度な整理にはAPIキーが必要です。

## Streamlit Community Cloudで公開する方法

1. GitHubで新しいリポジトリを作ります。
2. このフォルダ内の `app.py_ver.1.py`、`requirements.txt`、`.streamlit/config.toml`、`README.md` をアップロードしてCommitします。
3. Streamlit Community Cloudで「Create app」を押し、作成したリポジトリを選びます。
4. Main file pathに `app.py_ver.1.py` を指定します。
5. Advanced settingsのSecretsに次を登録します。

```toml
OPENAI_API_KEY = "実際のAPIキー"
```

6. Deployを押します。

`secrets.toml`本体やAPIキーはGitHubへアップロードしないでください。

## データの扱い

AI整理と音声文字起こしを使う場合、入力内容または録音内容がOpenAI APIへ送信されます。病院などで利用する場合は、氏名、住所、電話番号など不要な個人情報を入力しない運用を推奨します。

## 将来拡張

状態と表示を画面単位、整理項目単位で分けているため、子ども向けの質問文や場面別プロンプトを追加できます。履歴保存を追加するときにSupabaseを接続します。

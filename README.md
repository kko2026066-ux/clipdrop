# Clipdrop

심플한 YouTube 영상/오디오 다운로드 웹 앱입니다.

## 실행 방법

```powershell
py -m pip install -r requirements.txt
py app.py
```

브라우저에서 `http://127.0.0.1:5000`을 열면 됩니다.

`tools/ffmpeg/ffmpeg-9.0.1-essentials_build/bin`에 포함된 FFmpeg를 자동으로 사용합니다.

## 인터넷에 공개하기

이 프로젝트는 `Dockerfile`과 `render.yaml`이 포함되어 있어 Render에서 배포할 수 있습니다.

1. 프로젝트를 GitHub 저장소에 올립니다.
2. Render에서 `New > Web Service`를 선택하고 GitHub 저장소를 연결합니다.
3. `Docker` 런타임으로 배포하면 `onrender.com` 공개 주소가 생성됩니다.

공개 주소가 생긴 뒤 Google Search Console에서 사이트를 등록하고 색인 생성을 요청하면 검색 노출을 시작할 수 있습니다. Google 검색 결과 반영 시점은 보장되지 않습니다.

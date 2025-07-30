# Building

`docker build -t memos-public-proxy .`

# Running locally

`docker run --rm --network host -e MEMOS_HOST=<memos host> -e MEMOS_PORT=80 memos-public-proxy`

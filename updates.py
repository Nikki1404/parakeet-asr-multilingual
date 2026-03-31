docker tag parakeet_asr_realtime:latest \
us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_v3:0.0.1

docker push \
us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_v3:0.0.1

(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual# docker push us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime:0.0.1
The push refers to repository [us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime]
Get "https://us-central1-docker.pkg.dev/v2/": read tcp 10.90.126.61:32810->74.125.68.82:443: read: connection reset by peer
(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual#


unset http_proxy
unset https_proxy
unset HTTP_PROXY
unset HTTPS_PROXY

export http_proxy="http://163.116.128.80:8080"
export https_proxy="http://163.116.128.80:8080"
export HTTP_PROXY="http://163.116.128.80:8080"
export HTTPS_PROXY="http://163.116.128.80:8080"

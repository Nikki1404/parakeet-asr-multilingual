docker tag parakeet_asr_realtime:latest \
us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_v3:0.0.1

docker push \
us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_v3:0.0.1

(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual# docker push us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime:0.0.1
The push refers to repository [us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime]
Get "https://us-central1-docker.pkg.dev/v2/": read tcp 10.90.126.61:32810->74.125.68.82:443: read: connection reset by peer
(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual#


did this 
  993  31/03/26 09:47:33 docker tag parakeet_asr_realtime:latest us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr:0.0.1
  994  31/03/26 09:49:07 gcloud auth configure-docker us-central1-docker.pkg.dev
  995  31/03/26 09:50:04 docker push us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr:0.0.1
  996  31/03/26 09:50:28 docker images
  997  31/03/26 09:50:49 docker rmi us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr
  998  31/03/26 09:50:57 docker images
  999  31/03/26 09:52:07 gcloud auth login
 1000  31/03/26 09:53:44 gcloud auth configure-docker us-central1-docker.pkg.dev
 1001  31/03/26 09:54:48 docker tag parakeet_asr_realtime:latest us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime:0.0.1
 1002  31/03/26 09:55:16 docker push us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime:0.0.1
 1003  31/03/26 09:56:53 unset https_proxy
 1004  31/03/26 09:56:59 unset http_proxy
 1005  31/03/26 09:57:11 unset HTTP_PROXY
 1006  31/03/26 09:57:20 unset HTTPS_PROXY
 1007  31/03/26 09:57:54 docker push us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime:0.0.1
 1008  31/03/26 09:58:29 history
(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual# export https_proxy="http://163.116.128.80:8080"
(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual# export http_proxy="https://163.116.128.80:8080"
(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual# docker push us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime:0.0.1
The push refers to repository [us-central1-docker.pkg.dev/emr-dgt-autonomous-uctr1-snbx/asr-parakeet-v3/parakeet_asr_realtime]
Get "https://us-central1-docker.pkg.dev/v2/": read tcp 10.90.126.61:53414->74.125.68.82:443: read: connection reset by peer
(base) root@EC03-E01-AICOE1:/home/CORP/re_nikitav/parakeet-asr-multilingual#

still getting same 

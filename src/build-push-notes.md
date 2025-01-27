## Login with your API Token
```
docker login registry.digitalocean.com
```

## Build your container image locally

```
docker build -t registry.digitalocean.com/goldmage/django-k8s:latest -f Dockerfile .
```

## Push your container image
```
docker push registry.digitalocean.com/goldmage/django-k8s --all-tags
```

Naturally, for all these steps replace `registry.digitalocean.com/cfe-k8s/` with your container registry and `django-k8s` with whatever image name you want to give your Django project.

kubectl apply -f k8s/apps/django-k8s-web.yaml

kubectl exec -it pod-name -- //bin//bash
source /opt/venv/bin/activate

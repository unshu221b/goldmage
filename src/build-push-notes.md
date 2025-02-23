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

kubectl apply -f k8s/apps/django-k8s-web.yaml
or
kubectl rollout restart deployment/django-k8s-web-deployment

kubectl exec -it pod-name -- //bin//bash
source /opt/venv/bin/activate
migrate



4. Update secrets (if needed)
```
kubectl delete secret django-k8s-prod-env
kubectl create secret generic django-k8s-prod-env --from-env-file=src/.env.prod

5. Check logs
kubectl logs -f deployment/django-k8s-web-deployment
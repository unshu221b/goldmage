## verify working with the right cluster
kubectl config current-context

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
kubectl apply -f k8s/apps/popup-store-1.yaml
or
kubectl rollout restart deployment/django-k8s-web-deployment
kubectl rollout restart deployment/popup-store-1-deployment

kubectl exec -it pod-name -- //bin//bash
source /opt/venv/bin/activate
migrate



4. Update secrets (if needed)
```
# For popup store
kubectl create secret generic popup-store-1-env --from-env-file=.env.popup-store-1
kubectl delete secret popup-store-1-env

# For prod
kubectl create secret generic django-k8s-prod-env --from-env-file=.env.prod
kubectl delete secret django-k8s-prod-env


5. Check logs
kubectl logs -f deployment/django-k8s-web-deployment

6. Commit and push
git add . ; git commit -m "feat: update hero section and styles" ; git push

kubectl get secrets
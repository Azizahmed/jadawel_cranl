```
cloudron install -l embeddings.{YOUR_DOMAIN} --image jadawel/embeddings:1.0.0
```

In the Jadawel app in Cloudron do:

```
cloudron env set JADAWEL_EMBEDDINGS_API_URL=https://embeddings.{YOUR_DOMAIN}
```

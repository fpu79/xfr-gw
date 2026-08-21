from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Transfer


def health(request):
    return JsonResponse({"status": "ok"})


def transfer_list(request):
    return render(request, "transfers/list.html", {"transfers": Transfer.objects.order_by("-fetched_at")})


def download(request, transfer_id):
    transfer = get_object_or_404(Transfer, pk=transfer_id)
    path = Path(transfer.local_path)
    if not path.is_file():
        raise Http404("Datei nicht gefunden")
    return FileResponse(path.open("rb"), as_attachment=True, filename=transfer.filename)

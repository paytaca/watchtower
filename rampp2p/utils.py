from django.core.signing import Signer
from django.core.exceptions import ValidationError

def verify_signature(request):

  public_key = request.META.get('PUBLIC_KEY')
  signature = request.META.get('SIGNATURE')
  data = request.data

  signer = Signer(public_key)
  try:
    signed_data = signer.unsign(signature)
    if signed_data != data:
      print('Signature is invalid')
      raise ValidationError
  except:
    print('Signature is invalid')
    raise ValidationError
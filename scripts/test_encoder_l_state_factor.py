import torch
from scripts.encoder_l_v1 import TransformerFull, MambaFull

def test_transformer_state_off_masks_phi():
    model=TransformerFull(12,state_on=False).eval()
    x=torch.randn(2,12)
    a=torch.randn(2,9)
    b=torch.randn(2,9)*100
    with torch.no_grad():
        ya=model(x,a); yb=model(x,b); yz=model(x,torch.zeros_like(a))
    assert torch.allclose(ya,yb,atol=0,rtol=0)
    assert torch.allclose(ya,yz,atol=0,rtol=0)

def test_transformer_state_on_uses_phi():
    model=TransformerFull(12,state_on=True).eval()
    x=torch.randn(2,12)
    a=torch.randn(2,9)
    b=torch.randn(2,9)*100
    with torch.no_grad():
        ya=model(x,a); yb=model(x,b)
    assert not torch.allclose(ya,yb)

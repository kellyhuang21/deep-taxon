from .. import train_test_loaders
from pytorch_lightning import LightningModule
import torch.optim as optim
import torch.nn as nn
import torch

from ...sequence import WindowChunkedDIFile
from ..loss import DistMSELoss

class AbstractLit(LightningModule):

    def __init__(self, hparams):
        super().__init__()
        self.hparams = hparams
        if self.hparams.manifold:
            self._loss = DistMSELoss()
        elif self.hparams.classify:
            self._loss = nn.CrossEntropyLoss()
        else:
            self._loss =  nn.MSELoss()

    def set_dataset(self, dataset, load=True, inference=False):
        kwargs = dict(random_state=self.hparams.seed,
                      batch_size=self.hparams.batch_size,
                      distances=self.hparams.manifold,
                      downsample=self.hparams.downsample)

        if inference:
            kwargs['distances'] = False
        tr, te, va = train_test_loaders(dataset, **kwargs)
        self.loaders = {'train': tr, 'test': te, 'validate': va}

    def _check_loaders(self):
        if not hasattr(self, 'loaders'):
            raise ValueError('No loaders available. Call set_dataset before fitting')

    def configure_optimizers(self):
        optimizer = optim.Adam(self.parameters(), lr=self.hparams.lr)
        #schedular = optim.lr_scheduler.StepLR(optimizer, step_size=1)
        #return optimizer, schedular
        return optimizer

    # TRAIN
    def train_dataloader(self):
        self._check_loaders()
        return self.loaders['train']

    def training_step(self, batch, batch_idx):
        idx, seqs, target, olen = batch
        output = self.forward(seqs)
        loss = self._loss(output, target)
        return {'loss': loss}

    def training_epoch_end(self, outputs):
        return {'log': outputs[0]}

    # VALIDATION
    def val_dataloader(self):
        self._check_loaders()
        return self.loaders['validate']

    def validation_step(self, batch, batch_idx):
        idx, seqs, target, olen = batch
        output = self(seqs)
        return {'val_loss': self._loss(output, target)}

    def validation_epoch_end(self, outputs):
        val_loss_mean = torch.stack([x['val_loss'] for x in outputs]).mean()
        return {'log': {'val_loss': val_loss_mean}}

    # TEST
    def test_dataloader(self):
        self._check_loaders()
        return self.loaders['test']

    def test_step(self, batch, batch_idx):
        idx, seqs, target, olen = batch
        output = self(seqs)
        return {'test_loss': self._loss(output, target)}

    def test_epoch_end(self, outputs):
        test_loss_mean = torch.stack([x['test_loss'] for x in outputs]).mean()
        return {'test_loss': test_loss_mean}

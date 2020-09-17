import glob
import json

import click

from data_pipeline import input_fn
from gpt2_model import *

_ROOT = os.path.abspath(os.path.dirname(__file__))
LOG_DIR = _ROOT + "/log"
MODEL_DIR = _ROOT + "/model"


@click.command()
@click.option('--num-layers', type=int, default=8, show_default=True, help="No. of decoder layers")
@click.option('--embedding-size', type=int, default=768, show_default=True, help="Embedding size")
@click.option('--num-heads', type=int, default=8, show_default=True, help="Number of heads")
@click.option('--dff', type=int, default=3072, show_default=True, help="Filter Size")
@click.option('--max-seq-len', type=int, default=515, show_default=True, help="Seq length")
@click.option('--vocab-size', type=int, default=32000, show_default=True, help="Vocab size")
@click.option('--optimizer', type=str, default="adam", show_default=True, help="optimizer type")
@click.option('--batch-size', type=int, default=8, show_default=True, help="optimizer type")
@click.option('--learning-rate', type=float, default=0.001, show_default=True, help="learning rate")
@click.option('--graph-mode', type=bool, default=False, show_default=True, help="TF run mode")
@click.option('--distributed', type=bool, default=False, show_default=True, help="distributed training")
def train(num_layers, embedding_size, num_heads, dff, max_seq_len, vocab_size,
          optimizer, batch_size, learning_rate, graph_mode, distributed):
	par_map = {"num_layers": num_layers, "d_model": embedding_size,
	           "num_heads": num_heads, "dff": dff,
	           "max_seq_len": max_seq_len, "vocab_size": vocab_size}

	exp_name = "_".join(['{}_{}'.format(k, v) for k, v in par_map.items()])

	if not os.path.exists(MODEL_DIR):
		os.makedirs(MODEL_DIR)

	with open(MODEL_DIR + '/model_par.json', 'w') as f:
		json.dump(par_map, f)

	tf_records = glob.glob((_ROOT + "/data/tf_records/*.tfrecord"))
	if distributed:
		dist_dataset = input_fn(tf_records, batch_size=batch_size)
		mirrored_strategy = tf.distribute.MirroredStrategy(devices=["/gpu:0", "/gpu:1"])
		dist_dataset = mirrored_strategy.experimental_distribute_dataset(dist_dataset)
		with mirrored_strategy.scope():

			model = Gpt2(num_layers, embedding_size, num_heads, dff, max_seq_len, vocab_size,
			             optimizer=optimizer, learning_rate=learning_rate)
			model.create_optimizer()
			model.create_checkpoint_manager(MODEL_DIR)
			model.create_summary_writer(LOG_DIR)

		model.mirrored_strategy = mirrored_strategy
		model.fit(dist_dataset)
	else:
		dataset = input_fn(tf_records, batch_size=batch_size)
		model = Gpt2(num_layers, embedding_size, num_heads, dff, max_seq_len, vocab_size,
		             optimizer=optimizer, learning_rate=learning_rate)
		model.create_optimizer()
		model.create_checkpoint_manager(MODEL_DIR)
		model.create_summary_writer(LOG_DIR)
		model.fit(dataset, graph_mode)
		print("Training Done................")


if __name__ == "__main__":
	train()

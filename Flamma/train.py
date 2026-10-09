from model.trainer import Trainer


def main():

    trainer = Trainer()

    trainer.train(epochs=1000)


if __name__ == "__main__":
    main()
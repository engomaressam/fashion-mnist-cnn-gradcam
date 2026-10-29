"""Build the deep-learning final project report (.docx) from the notebook results; export_pdf.ps1 makes the PDF.

usage: python build_report.py
"""
from pathlib import Path

import pandas as pd
from docx.enum.text import WD_ALIGN_PARAGRAPH

from docx_helpers import (DARK_BLUE, MUTED, NAVY, SECONDARY, bullets, callout, figure, footer, heading, new_document,
                          page_break, para, stat_row, table, table_of_contents)

SOURCE = Path(__file__).resolve().parent
PROJECT = SOURCE.parent
RESULTS, FIGURES = PROJECT / "results", PROJECT / "figures"
OUTPUT = PROJECT / "Deep Learning - Final Project Report.docx"

AUTHOR = "Omar Essam"
DATE = "October 24, 2026"
L, R = WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT

ARCHITECTURE = {
    "Dense network (MLP)": "Flatten - Dense 256 - Dropout 0.3 - Dense 128 - Dropout 0.3 - softmax",
    "Small CNN": "Conv 32 (3x3) - MaxPool - Conv 64 (3x3) - MaxPool - Dense 128 - Dropout 0.3 - softmax",
    "Deep CNN (BatchNorm + Dropout)": "3 VGG-style blocks: 2 x Conv 32, 2 x Conv 64, Conv 128 (3x3, BatchNorm, ReLU), MaxPool + Dropout 0.25 after each; Dense 128 - Dropout 0.4 - softmax",
    "Deep CNN + data augmentation": "Same deep CNN, trained on images randomly flipped left-right, shifted and zoomed by up to 8%",
}


def csv(name):
    return pd.read_csv(RESULTS / name)


def pct(x, digits=1):
    return f"{x:.{digits}%}"


def as_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def main():
    summary = csv("summary.csv").set_index("metric")["value"].map(as_number)  # mixed text and numbers
    comp = csv("model_comparison.csv").set_index("model")
    per_class = csv("per_class.csv").set_index("class")
    cover = csv("coverage_accuracy.csv")
    confusions = csv("top_confusions.csv")
    hist = csv("training_history.csv")

    final = summary["final_model"]
    f = comp.loc[final]
    order = list(comp.index)
    ranked = comp.sort_values("test_acc", ascending=False)
    runner = ranked.index[1]
    mlp, small = comp.loc["Dense network (MLP)"], comp.loc["Small CNN"]
    deep, aug = comp.loc["Deep CNN (BatchNorm + Dropout)"], comp.loc["Deep CNN + data augmentation"]
    error_cut = 1 - (1 - f["test_acc"]) / (1 - mlp["test_acc"])  # relative reduction of the test error vs the dense network
    # highest coverage that still reaches 99% accuracy
    c99 = cover[cover["accuracy"] >= 0.99].sort_values("coverage", ascending=False).iloc[0]
    c90 = cover[cover["threshold"] == 0.9].iloc[0]
    weakest = per_class["recall"].idxmin()
    strongest = per_class["recall"].sort_values(ascending=False).index[:3]
    top = confusions.iloc[0]
    gap = lambda r: r["train_acc"] - r["test_acc"]

    doc = new_document()

    # ------------------------------------------------------------------ cover
    para(doc, [("IBM Machine Learning Professional Certificate  |  Deep Learning and Reinforcement Learning - Final Project", {"color": MUTED, "size": 9.5})], after=60)
    para(doc, [("Automatic Product-Image Tagging", {"bold": True, "color": NAVY, "size": 30})], after=2)
    para(doc, [("Which neural network should tag the fashion catalogue, and how much of the work can it take over?", {"color": DARK_BLUE, "size": 15})], after=18)
    para(doc, [("A stakeholder report comparing four deep-learning variations - a dense network and three convolutional neural networks - "
                "for classifying product images, with a recommended model, what it gets right and wrong, and how to deploy it safely.",
                {"color": SECONDARY, "size": 11})], after=26)
    stat_row(doc, [(pct(f["test_acc"]), "test accuracy of the recommended CNN on 10,000 unseen product images"),
                   (pct(c99["coverage"], 0), f"of images can be tagged automatically at {pct(c99['accuracy'])} accuracy (confidence >= {c99['threshold']:g})"),
                   (f"{error_cut:.0%}", "fewer wrong tags than a standard dense neural network")])
    para(doc, "", after=30)
    table(doc, [["Prepared for", "Chief Data Officer and Head of Analytics"],
                ["Prepared by", f"{AUTHOR}, Data Scientist"],
                ["Date", DATE],
                ["Analysis behind this report", "Final Project/Deep Learning - Fashion Product Image Classification.ipynb"]],
          [4.4, 12.2], header=False, size=10, bold_first_col=True)
    page_break(doc)

    # ------------------------------------------------------------------ contents + executive summary
    para(doc, [("Contents", {"bold": True, "color": NAVY, "size": 15})], after=4)
    table_of_contents(doc)
    heading(doc, "Executive summary", 1)
    para(doc, "An online fashion retailer adds thousands of product photos to its catalogue every week, and each one has to be tagged with its "
              "category before it can be searched, filtered and recommended. This analysis trains deep-learning models that read a product image and "
              "predict its category, and asks how much of the tagging work they can safely automate.")
    para(doc, [("Key insights", {"bold": True, "color": DARK_BLUE})], after=2, keep_next=True)
    bullets(doc, [
        [("Convolutions matter. ", {"bold": True}),
         (f"The recommended CNN reaches {pct(f['test_acc'])} test accuracy against {pct(mlp['test_acc'])} for a dense network that treats pixels independently - "
          f"{error_cut:.0%} fewer wrong tags.", {})],
        [("Regularised depth wins. ", {"bold": True}),
         (f"Batch normalisation and dropout let the deeper CNN reach the best accuracy with a small train-test gap ({gap(deep) * 100:.1f} points). Data augmentation "
          f"shrank the gap further ({gap(aug) * 100:.1f} points) but was still improving when the {int(aug['epochs_run'])}-epoch CPU budget ran out.", {})],
        [("Most products are easy; tops are hard. ", {"bold": True}),
         (f"{', '.join(strongest)} are recognised almost perfectly, while {weakest} is the weakest class (recall {pct(per_class.loc[weakest, 'recall'], 0)}); the most common "
          f"mix-up is {top['true']} tagged as {top['predicted']} ({int(top['count'])} of 1,000 test images).", {})],
        [("Confidence makes automation safe. ", {"bold": True}),
         (f"Accepting only predictions with confidence of at least {c99['threshold']:g} tags {pct(c99['coverage'], 0)} of images at {pct(c99['accuracy'])} accuracy; the "
          f"remaining {pct(1 - c99['coverage'], 0)} go to a human tagger.", {})],
    ])
    callout(doc, "Recommendation", [
        [(f"Deploy the {final} as a human-in-the-loop tagger: ", {"bold": True}),
         (f"auto-accept tags above confidence {c99['threshold']:g} and route the rest to the catalogue team. It is the most accurate variation "
          f"({pct(f['test_acc'])}, macro F1 {f['test_f1_macro']:.3f}), remains small ({int(f['parameters']):,} parameters) and tags an image in about "
          f"{f['infer_ms_per_image']:.2f} ms on an ordinary CPU.", {})],
        [("Next: ", {"bold": True}),
         ("retrain on the retailer's own colour photos with transfer learning, and add product text (title, description) to separate shirts from tops.", {})],
    ])
    page_break(doc)

    # ------------------------------------------------------------------ 1. objective
    heading(doc, "1. Main objective of the analysis", 1)
    para(doc, [("The objective is to automate the tagging of product images with supervised deep learning, specifically convolutional neural "
                "networks (CNNs) for multi-class image classification. ", {"bold": True}),
               ("The model has to predict which of ten categories a product image belongs to, as accurately as possible on images it has never seen, "
                "and it has to say how sure it is, so that the business can decide which tags to trust automatically. The focus is on prediction "
                "accuracy, supported by explanations (confusion analysis, learned filters and Grad-CAM heatmaps) that show stakeholders why the "
                "model can be trusted and where it cannot.", {})])
    para(doc, "The benefits for the business are:")
    bullets(doc, [
        [("Faster time to market: ", {"bold": True}), ("new products are searchable as soon as their photo is uploaded.", {})],
        [("Lower tagging cost: ", {"bold": True}), ("people only review the uncertain images instead of every image.", {})],
        [("Better catalogue data quality: ", {"bold": True}), ("consistent categories improve search, filters, recommendations and reporting.", {})],
        [("A reusable capability: ", {"bold": True}), ("the same approach can flag mislabelled products already in the catalogue.", {})],
    ])

    # ------------------------------------------------------------------ 2. data
    heading(doc, "2. Data description", 1)
    para(doc, [("The data is ", {}), ("Fashion-MNIST", {"bold": True}),
               (f", published by Zalando Research as a public benchmark built from Zalando's own product photos: {int(summary['train_images'] + summary['val_images']):,} "
                f"training and {int(summary['test_images']):,} test images of articles from ten categories, exactly 7,000 per category. It stands in for the "
                "retailer's catalogue images.", {})])
    table(doc, [
        ["Element", "Description", "Use in the deep-learning task"],
        ["Image", "28 x 28 pixels, grayscale, the product centred on a white background", "Input of the network (one channel)"],
        ["Pixel values", "784 intensities per image, 0 (white) to 255 (black)", "Scaled to 0-1; local patterns of pixels are what the convolutions learn"],
        ["Label", "10 categories: T-shirt/top, Trouser, Pullover, Dress, Coat, Sandal, Shirt, Sneaker, Bag, Ankle boot", "Target of the softmax output layer"],
        ["Split", f"{int(summary['train_images']):,} training, {int(summary['val_images']):,} validation (from the official training set), {int(summary['test_images']):,} test", "Training, early stopping, final comparison"],
    ], [2.4, 7.4, 6.8], size=9)
    figure(doc, FIGURES / "fig1_samples.png", "Figure 1 - Five random training images of each category. Shirts, T-shirts/tops, pullovers and coats look alike at this resolution.")
    para(doc, "The analysis aims to find the deep-learning architecture that classifies these images most accurately, understand its mistakes, "
              "and turn its confidence scores into a practical automation rule.")

    # ------------------------------------------------------------------ 3. exploration & preparation
    heading(doc, "3. Data exploration and preparation", 1)
    bullets(doc, [
        "The classes are perfectly balanced (6,000 training and 1,000 test images each), so accuracy is a fair headline metric; macro F1 is reported as well.",
        (f"Data quality: no missing values, no exact duplicate images inside the training set and no test image that also occurs in the training set "
         "(checked by hashing every image), so there is no leakage between training and evaluation."
         if int(summary["duplicates_in_train"]) == 0 and int(summary["test_in_train"]) == 0 else
         f"Data quality: no missing values; {int(summary['duplicates_in_train'])} exact duplicate images inside the training set and "
         f"{int(summary['test_in_train'])} test images that also occur in the training set."),
        f"Mean pixel intensity differs by class ({summary['mean_pixel_darkest_class']} is the darkest), but shape and texture - not brightness - separate the confusable tops, which motivates convolutions.",
        "Preparation: pixels scaled to 0-1 and reshaped to 28 x 28 x 1; a stratified 6,000-image validation set was held out of the official training images for early stopping, and the official test set was kept untouched for the final comparison.",
        "Feature engineering is learned by the network itself: each convolution kernel is a small 3 x 3 grid of weights slid across the image to detect a local pattern such as an edge or a texture. Without padding a 3 x 3 kernel turns a 28 x 28 image into 26 x 26 (and a 3 x 3 image into a single value); 'same' padding keeps 28 x 28 so the borders are not lost.",
        "Data augmentation (variation 4) creates new training views on the fly - mirror images, shifts and zooms of up to 8% - so the network learns that a product is the same product wherever it sits in the frame.",
    ])

    # ------------------------------------------------------------------ 4. model variations
    heading(doc, "4. Model variations", 1)
    para(doc, "Four variations were trained on the same 54,000 images with the same optimiser (Adam, learning rate 0.001, batch 128), early stopping "
              "on validation loss (patience 5, best weights kept) and learning-rate halving on plateaus:")
    rows = [["Variation", "Architecture"]] + [[[(n, {"bold": True})], ARCHITECTURE[n]] for n in order]
    table(doc, rows, [4.6, 12.0], size=9)
    rows = [["Variation", "Parameters", "Epochs", "Train min", "Train acc", "Test acc [95% CI]", "Macro F1", "ms / image"]]
    for n in order:
        r = comp.loc[n]
        rows.append([n, f"{int(r['parameters']):,}", f"{int(r['epochs_run'])}", f"{r['train_minutes']:.1f}", pct(r["train_acc"]),
                     f"{pct(r['test_acc'])} [{pct(r['acc_ci_low'])}-{pct(r['acc_ci_high'])}]", f"{r['test_f1_macro']:.3f}", f"{r['infer_ms_per_image']:.2f}"])
    table(doc, rows, [4.4, 1.9, 1.3, 1.5, 1.6, 3.2, 1.5, 1.6], aligns=[L, R, R, R, R, R, R, R], size=8.5, highlight_rows=(order.index(final) + 1,))
    figure(doc, FIGURES / "fig2_training_comparison.png", "Figure 2 - Validation accuracy during training (left) and training vs test accuracy of each variation (right); "
                                                          "a wide gap between the gray and blue dots means the model memorised the training images.")
    bullets(doc, [
        [("Dense network: ", {"bold": True}), (f"{pct(mlp['test_acc'])} test accuracy. Flattening the image throws away which pixels are neighbours, and it overfits the most "
                                               f"(training accuracy {pct(mlp['train_acc'])}).", {})],
        [("Small CNN: ", {"bold": True}), (f"{pct(small['test_acc'])} with far fewer epochs: two convolution blocks already capture edges and textures, "
                                           f"but the train-test gap ({gap(small) * 100:.1f} points) shows it starts to memorise.", {})],
        [("Deep CNN with batch normalisation and dropout: ", {"bold": True}), (f"{pct(deep['test_acc'])}; more capacity, while dropout and batch normalisation keep the gap at "
                                                                              f"{gap(deep) * 100:.1f} points.", {})],
        [("Deep CNN with data augmentation: ", {"bold": True}), (f"{pct(aug['test_acc'])}; augmentation is the strongest regulariser (gap {gap(aug) * 100:.1f} points), "
                                                                 f"but harder training images make learning slower: it used all {int(aug['epochs_run'])} epochs, its best epoch was "
                                                                 f"{int(aug['best_epoch'])} and validation accuracy was still rising - it is under-trained "
                                                                 f"rather than worse, and the longest to train ({aug['train_minutes']:.0f} minutes on a CPU).", {})],
    ])
    diff = comp.loc[final, "diff_vs_second"]
    para(doc, f"The 95% bootstrap interval of the accuracy difference between the best variation ({final}) and the runner-up ({runner}) is {diff}"
              + (" - the ranking is statistically clear." if isinstance(diff, str) and not diff.startswith("-") and "to -" not in diff else
                 " - the two are close, so cost and robustness also weigh in the choice."))

    # ------------------------------------------------------------------ 5. recommendation
    heading(doc, "5. Recommended final model", 1)
    para(doc, [(f"Recommended: the {final}. ", {"bold": True}),
               ("It best fits the objective of accurate, trustworthy automatic tagging:", {})])
    bullets(doc, [
        [("Most accurate: ", {"bold": True}), (f"{pct(f['test_acc'])} test accuracy and macro F1 {f['test_f1_macro']:.3f}, the best of the four variations.", {})],
        [("Generalises well: ", {"bold": True}), (f"training and test accuracy differ by only {gap(f) * 100:.1f} points, so performance on new products should hold up.", {})],
        [("Cheap to run: ", {"bold": True}), (f"{int(f['parameters']):,} parameters and about {f['infer_ms_per_image']:.2f} ms per image on a CPU - no GPU is needed to tag the catalogue.", {})],
        [("Explainable enough for the business: ", {"bold": True}), ("its confidence scores are reliable for routing (section 6), and Grad-CAM heatmaps show that it reads each product's silhouette - sleeves, hems, handles and outline.", {})],
    ])
    para(doc, "The dense network is simpler to explain mathematically but makes many more mistakes, so it is not recommended; the small CNN is a "
              "reasonable fallback where training time matters more than the last point of accuracy.")

    # ------------------------------------------------------------------ 6. findings
    heading(doc, "6. Key findings and insights", 1)
    heading(doc, "Where the model is right and wrong", 2)
    figure(doc, FIGURES / "fig3_confusion_matrix.png", "Figure 3 - Confusion matrix of the recommended model (diagonal = recall per class; off-diagonal = number of test images).", width_cm=12.5)
    rows = [["Class", "Precision", "Recall", "F1"]]
    for cls, r in per_class.sort_values("recall").iterrows():
        rows.append([cls, pct(r["precision"]), pct(r["recall"]), f"{r['f1-score']:.3f}"])
    table(doc, rows, [5.0, 3.0, 3.0, 3.0], aligns=[L, R, R, R], size=9, highlight_rows=(1,))
    bullets(doc, [
        f"Footwear, bags and trousers are recognised almost perfectly: their silhouettes are distinctive.",
        f"Upper-body garments are the hard group. {weakest} has the lowest recall ({pct(per_class.loc[weakest, 'recall'])}); the most frequent confusions are "
        + "; ".join(f"{r.true} tagged as {r.predicted} ({int(r.count)})" for r in confusions.head(3).itertuples()) + ".",
        [("The most confident mistakes point to label errors, not model errors (Figure 4): ", {"bold": True}),
         ("images labelled 'Sneaker' that are clearly high-top boots, a 'T-shirt/top' that is a sleeveless dress, a 'Shirt' that looks like a bag. In these cases the "
          "model's answer is arguably the right one, so part of the measured error sits in the data, and the model can be used to find mislabelled products.", {})],
    ])
    figure(doc, FIGURES / "fig7_confident_mistakes_2rows.png", "Figure 4 - The ten mistakes made with the highest confidence (true label, predicted label, confidence). Most look mislabelled rather than misread.", width_cm=12.0)
    heading(doc, "How much tagging can be automated", 2)
    figure(doc, FIGURES / "fig4_coverage_accuracy.png", "Figure 5 - If only predictions above a confidence threshold are accepted automatically, accuracy rises while coverage falls "
                                                        "(two thresholds marked; the table below lists more).", width_cm=13.5)
    rows = [["Confidence threshold", "Tagged automatically", "Accuracy of automatic tags", "Sent to human review"]]
    for r in cover[cover["threshold"].isin([0.0, 0.7, 0.9, 0.95, 0.99])].itertuples():
        rows.append([f"{r.threshold:g}" if r.threshold else "none (accept all)", pct(r.coverage), pct(r.accuracy, 2), pct(r.sent_to_review)])
    table(doc, rows, [4.2, 3.8, 4.6, 4.0], aligns=[L, R, R, R], size=9.5,
          highlight_rows=(list(cover[cover["threshold"].isin([0.0, 0.7, 0.9, 0.95, 0.99])]["threshold"]).index(c99["threshold"]) + 1,))
    para(doc, f"At a threshold of {c99['threshold']:g}, {pct(c99['coverage'], 0)} of new product images are tagged without human effort at {pct(c99['accuracy'])} "
              f"accuracy, and the catalogue team only reviews {pct(1 - c99['coverage'], 0)}. A looser threshold of 0.9 automates {pct(c90['coverage'], 0)} at "
              f"{pct(c90['accuracy'])}. The threshold is a business decision that trades review cost against the cost of a wrong tag.")
    heading(doc, "What the network has learned", 2)
    figure(doc, FIGURES / "fig5_kernels_feature_maps.png", "Figure 6 - Seven of the first-layer 3 x 3 kernels (top) and the feature maps they produce for one ankle boot (bottom): each kernel responds to a different edge orientation or texture.")
    figure(doc, FIGURES / "fig6_gradcam.png", "Figure 7 - Grad-CAM heatmaps of the last convolution layer: the regions that drive each prediction (red). The model reads outlines - sleeve ends, hems, handles - and the empty space around them.")
    para(doc, "The first convolution layer has learned edge and texture detectors - the 'kernels' of a CNN - and deeper layers combine them into "
              "parts of the silhouette. Grad-CAM shows that the decisive evidence is the outline: the ends of sleeves, the hem, the handle of a bag, "
              "and for sneakers and dresses the empty space around the product (a low shoe leaves the top of the frame empty, which separates it from "
              "an ankle boot). In the misclassified shirt the model looks at the short sleeve, which is exactly why it reads the item as a T-shirt. "
              "Reasoning from silhouettes works on clean studio images, but it is also a risk for photos with busy backgrounds (section 7).")

    # ------------------------------------------------------------------ 7. limitations
    heading(doc, "7. Limitations of the model", 1)
    bullets(doc, [
        [("Benchmark images, not the real catalogue: ", {"bold": True}), ("28 x 28 grayscale photos on clean backgrounds are much simpler than real colour photos with models, props and varying light; accuracy will drop on production images until the model is retrained on them.", {})],
        [("Only ten broad categories: ", {"bold": True}), ("a real catalogue has hundreds of categories and attributes (colour, sleeve length, pattern); the model cannot tag what it has not been trained on.", {})],
        [("Ambiguous classes and noisy labels: ", {"bold": True}), (f"the {weakest} / T-shirt boundary is inherently fuzzy at this resolution, and several of the most confident 'mistakes' are mislabelled images, so the test score is a noisy measure of the true quality.", {})],
        [("Reliance on silhouette and background: ", {"bold": True}), ("Grad-CAM shows the model uses the empty space around a product as evidence; cluttered or cropped production photos could mislead it.", {})],
        [("Confidence is not certainty: ", {"bold": True}), (f"{pct(summary['confident_mistake_share'], 0)} of the mistakes are still made with confidence of at least 0.9, so automatic tags need periodic audits.", {})],
        [("Single training run and CPU budget: ", {"bold": True}), ("each variation was trained once with one random seed, the augmented model was stopped by the epoch cap while still improving, and architectures and hyper-parameters were not searched exhaustively.", {})],
    ])

    # ------------------------------------------------------------------ 8. next steps
    heading(doc, "8. Next steps", 1)
    bullets(doc, [
        [("Transfer learning on real photos: ", {"bold": True}), ("fine-tune a pre-trained network (for example EfficientNet or ResNet) on the retailer's own colour images at higher resolution.", {})],
        [("Add product text: ", {"bold": True}), ("combine the image with the title and description in a multimodal model - words such as 'button-down' or 'collar' resolve the shirt vs T-shirt confusion.", {})],
        [("Calibrate and monitor confidence: ", {"bold": True}), ("apply temperature scaling, track accuracy of auto-accepted tags in production, and adjust the threshold to the cost of errors.", {})],
        [("Clean the labels with the model: ", {"bold": True}), ("review the most confident mistakes to fix mislabelled images, and collect more examples of the confusable tops.", {})],
        [("Finish the augmented model, then tune and ensemble: ", {"bold": True}), ("train the augmented CNN to convergence on a GPU (it was still improving), search learning rates, depth and augmentation strength, and average several CNNs.", {})],
        [("Pilot in the catalogue workflow: ", {"bold": True}), ("start with one product line, compare tagging time and error rates with the manual process, then scale.", {})],
    ])

    # ------------------------------------------------------------------ appendix
    heading(doc, "Appendix: training set-up and reproducibility", 1).paragraph_format.page_break_before = True
    table(doc, [
        ["Setting", "Value"],
        ["Optimiser", "Adam, learning rate 0.001, halved after 2 epochs without validation improvement (minimum 0.00001)"],
        ["Batch size / epochs", "128 / up to 30-40 with early stopping on validation loss (patience 5, best weights restored)"],
        ["Loss and output", "sparse categorical cross-entropy, 10-way softmax"],
        ["Regularisation", "dropout 0.25-0.4, batch normalisation (deep CNNs), random flip / shift / zoom (variation 4)"],
        ["Evaluation", "official 10,000-image test set; 95% bootstrap intervals from 1,000 resamples"],
    ], [4.2, 12.4], size=9.5, bold_first_col=True)
    bullets(doc, [
        "Data: Fashion-MNIST (github.com/zalandoresearch/fashion-mnist), loaded with keras.datasets.fashion_mnist.",
        "Analysis: Final Project/Deep Learning - Fashion Product Image Classification.ipynb - every table and figure in this report is produced there and saved to the results and figures folders.",
        "Environment: Python 3.11, TensorFlow 2.17 / Keras 3, scikit-learn 1.5, matplotlib 3.9; trained on CPU; random seed 123.",
        "This report: Final Project/source/build_report.py builds it from the saved results; export_pdf.ps1 updates the contents and saves the PDF with Microsoft Word.",
    ])

    footer(doc, "Automatic Product-Image Tagging - Deep Learning final project")
    doc.core_properties.author = AUTHOR
    doc.core_properties.title = "Automatic Product-Image Tagging - Deep Learning Final Project"
    doc.save(OUTPUT)
    print("saved", OUTPUT)


if __name__ == "__main__":
    main()

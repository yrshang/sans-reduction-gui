window.prepare_charts = function() {
    window.document.querySelectorAll('.vega-embed').forEach((chart) => {
        // This violates the MVVM package pattern, but it's important to do here since I need to immediately disable interactivity here.
        // There is an issue to handle these Vega charts in a more Trame-friendly way, but until that's complete I'd strongly recommend leaving this as is.
        window.trame.state.set('stitching_in_progress', true);

        const name = chart.getAttribute('name');
        const index = name[name.length - 1] - 1;

        // This is important as we are letting each chart resize with its parent. An odd quirk of
        // Vega is that it sometimes won't render in Vue when using its parent's width until the window
        // is resized, so I trigger it manually here.
        window.dispatchEvent(new window.Event('resize'));

        const ref = window.trame.refs[`stitching_${index}`];
        // Not 100% on why the timeout is necessary. Without it, the event listener is lost any time the chart is updated.
        window.setTimeout(() => {
            ref.viz.view.addEventListener(
                'pointerup',
                () => {
                    if (Object.hasOwn(ref.viz.view._signals, 'select')) {
                        // This chart has an interval selection signal, so we can safely fire an interval selection event.
                        if (ref.viz.view._signals.select.value.x !== undefined) {
                            window.trame.state.set('stitching_in_progress', true);
                            window.trame.trigger('interval_selection', [index, ref.viz.view._signals.select.value.x]);
                        }
                    }
                },
                { once: true });

            window.trame.state.set('stitching_in_progress', false);
        }, 250);
    });
}

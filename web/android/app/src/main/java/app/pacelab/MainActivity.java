package app.pacelab;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        // plugins próprios do app precisam ser registrados antes do super.onCreate (docs do Capacitor)
        registerPlugin(SamsungHealthPlugin.class);
        registerPlugin(AtualizacaoPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
